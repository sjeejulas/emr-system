
from common.functions import send_mail
from django.template import loader
from django.conf import settings
from zipfile import ZipFile, ZIP_DEFLATED
from .models import PatientReportAuth, ThirdPartyAuthorisation, UnsupportedAttachment
from instructions.models import Instruction
from imutils.object_detection import non_max_suppression
from medicalreport.models import ReferencePhrases
import pytesseract
import cv2
import scipy.misc
import img2pdf
import PyPDF2

import json
import logging
import io
import uuid
import os
import numpy as np

event_logger = logging.getLogger('medidata.event')

#todo add link
def send_patient_mail(patient, gp_practice):
    send_mail(
        'Notification from your GP surgery',
        'Your instruction has been submitted',
        'MediData',
        [patient.email],
        fail_silently=True,
        html_message=loader.render_to_string('medicalreport/patient_email.html', {
            'gp': gp_practice.name,
            'link': 'just a link'
        })
    )


def validate_pin(
        response, pin: str,  patient_auth: PatientReportAuth,
        access_type: str, third_party_authorisation: ThirdPartyAuthorisation=None, otp_type: str=''
) -> bool:
    max_input = 3
    if response.status_code == 200:
        response_results_dict = json.loads(response.text)
        if access_type == PatientReportAuth.ACCESS_TYPE_PATIENT:
            if response_results_dict['validated']:
                patient_auth.verify_pin = pin
                patient_auth.count = 0
                patient_auth.save()
                event_logger.info(
                    '{access_type} VERIFIED OTP successful, Instruction ID {instruction_id}'.format(
                        access_type=access_type, instruction_id=patient_auth.instruction.id)
                )
                return True
            else:
                patient_auth.count = patient_auth.count + 1
                if patient_auth.count >= max_input:
                    patient_auth.locked_report = True
                    patient_auth.count = 0
                patient_auth.save()
        elif access_type == PatientReportAuth.ACCESS_TYPE_THIRD_PARTY:
            if response_results_dict['validated']:
                if otp_type == 'sms':
                    third_party_authorisation.verify_sms_pin = pin
                elif otp_type == 'voice':
                    third_party_authorisation.verify_voice_pin = pin
                third_party_authorisation.count = 0
                third_party_authorisation.save()
                event_logger.info(
                    '{access_type} VERIFIED OTP successful, Instruction ID {instruction_id}'.format(
                        access_type=access_type, instruction_id=patient_auth.instruction.id)
                )
                return True
            else:
                third_party_authorisation.count = third_party_authorisation.count + 1
                if third_party_authorisation.count >= max_input:
                    third_party_authorisation.locked_report = True
                    third_party_authorisation.count = 0
                third_party_authorisation.save()

        if not response_results_dict['validated']:
            event_logger.info(
                '{access_type} VERIFIED OTP failed, Instruction ID {instruction_id}'.format(
                    access_type=access_type, instruction_id=patient_auth.instruction.id)
            )

    return False


def get_zip_medical_report(instruction: Instruction):
    path_patient = instruction.patient_information.__str__()
    path = settings.MEDIA_ROOT + '/patient_attachments/' + path_patient + '/'
    with ZipFile(path + 'medicalreports.zip', 'w', ZIP_DEFLATED) as zip:
        zip.writestr('medical_report.pdf', bytes(instruction.medical_with_attachment_report_byte))
        for unsupported_attachment in UnsupportedAttachment.objects.filter(instruction_id=instruction.id):
            zip.writestr(unsupported_attachment.file_name, bytes(unsupported_attachment.file_content))
    return open(path + 'medicalreports.zip', 'rb')


def decode_predictions(scores, geometry, min_confident=0.5):
    # grab the number of rows and columns from the scores volume, then
    # initialize our set of bounding box rectangles and corresponding
    # confidence scores
    (numRows, numCols) = scores.shape[2:4]
    rects = []
    confidences = []

    # loop over the number of rows
    for y in range(0, numRows):
        # extract the scores (probabilities), followed by the
        # geometrical data used to derive potential bounding box
        # coordinates that surround text
        scoresData = scores[0, 0, y]
        xData0 = geometry[0, 0, y]
        xData1 = geometry[0, 1, y]
        xData2 = geometry[0, 2, y]
        xData3 = geometry[0, 3, y]
        anglesData = geometry[0, 4, y]

        # loop over the number of columns
        for x in range(0, numCols):
            # if our score does not have sufficient probability,
            # ignore it
            if scoresData[x] < min_confident:
                continue

            # compute the offset factor as our resulting feature
            # maps will be 4x smaller than the input image
            (offsetX, offsetY) = (x * 4.0, y * 4.0)

            # extract the rotation angle for the prediction and
            # then compute the sin and cosine
            angle = anglesData[x]
            cos = np.cos(angle)
            sin = np.sin(angle)

            # use the geometry volume to derive the width and height
            # of the bounding box
            h = xData0[x] + xData2[x]
            w = xData1[x] + xData3[x]

            # compute both the starting and ending (x, y)-coordinates
            # for the text prediction bounding box
            endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
            endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
            startX = int(endX - w)
            startY = int(endY - h)

            # add the bounding box coordinates and probability score
            # to our respective lists
            rects.append((startX, startY, endX, endY))
            confidences.append(scoresData[x])

    # return a tuple of the bounding boxes and associated confidences
    return (rects, confidences)


def redaction_image(image_path, east_path, width=960, height=960, padding=0.0, patient_info={}):
    event_logger.info('Image Redaction Processing...')
    image = cv2.imread(image_path)
    orig = image.copy()
    (origH, origW) = image.shape[:2]

    # set the new width and height and then determine the ratio in change
    # for both the width and height
    (newW, newH) = (width, height)
    rW = origW / float(newW)
    rH = origH / float(newH)

    # resize the image and grab the new image dimensions
    image = cv2.resize(image, (newW, newH))
    (H, W) = image.shape[:2]

    # define the two output layer names for the EAST detector model that
    # we are interested -- the first is the output probabilities and the
    # second can be used to derive the bounding box coordinates of text
    layerNames = [
        "feature_fusion/Conv_7/Sigmoid",
        "feature_fusion/concat_3"]

    # load the pre-trained EAST text detector
    net = cv2.dnn.readNet(east_path)

    # construct a blob from the image and then perform a forward pass of
    # the model to obtain the two output layer sets
    blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
                                 (123.68, 116.78, 103.94), swapRB=True, crop=False)
    net.setInput(blob)
    (scores, geometry) = net.forward(layerNames)

    # decode the predictions, then  apply non-maxima suppression to
    # suppress weak, overlapping bounding boxes
    (rects, confidences) = decode_predictions(scores, geometry)
    boxes = non_max_suppression(np.array(rects), probs=confidences)

    # initialize the list of results
    results = []

    # loop over the bounding boxes
    for (startX, startY, endX, endY) in boxes:
        # scale the bounding box coordinates based on the respective
        # ratios
        startX = int(startX * rW)
        startY = int(startY * rH)
        endX = int(endX * rW)
        endY = int(endY * rH)

        # in order to obtain a better OCR of the text we can potentially
        # apply a bit of padding surrounding the bounding box -- here we
        # are computing the deltas in both the x and y directions
        dX = int((endX - startX) * padding)
        dY = int((endY - startY) * padding)

        # apply padding to each side of the bounding box, respectively
        startX = max(0, startX - dX)
        startY = max(0, startY - dY)
        endX = min(origW, endX + (dX * 2))
        endY = min(origH, endY + (dY * 2))

        # extract the actual padded ROI
        roi = orig[startY:endY, startX:endX]

        # in order to apply Tesseract v4 to OCR text we must supply
        # (1) a language, (2) an OEM flag of 4, indicating that the we
        # wish to use the LSTM neural net model for OCR, and finally
        # (3) an OEM value, in this case, 7 which implies that we are
        # treating the ROI as a single line of text
        config = ("-l eng --oem 1 --psm 6")
        text = pytesseract.image_to_string(roi, config=config)

        # add the bounding box coordinates and OCR'd text to the list
        # of results
        results.append(((startX, startY, endX, endY), text))

    # sort the results bounding box coordinates from top to bottom
    results = sorted(results, key=lambda r: r[0][1])

    # get all words to redaction from image
    redact_words = list(ReferencePhrases.objects.all().values_list('name', flat=True))

    # loop over the results
    output = orig.copy()
    redacted_count = 0
    for ((startX, startY, endX, endY), text) in results:
        # strip out non-ASCII text so we can draw the text on the image
        # using OpenCV, then draw the text and a bounding box surrounding
        # the text region of the input image
        text = "".join([c if ord(c) < 128 else "" for c in text]).strip()
        if patient_info['first_name'] in redact_words:
            redact_words.remove(patient_info['first_name'])
        if patient_info['last_name'] in redact_words:
            redact_words.remove(patient_info['last_name'])
        if text in redact_words:
            cv2.rectangle(output, (startX, startY), (endX, endY), (0, 0, 0), -1)
            redacted_count += 1

    unique = uuid.uuid4().hex
    image_name = 'outfile_{unique}.jpg'.format(unique=unique)
    image_to_write = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)
    scipy.misc.imsave(image_name, image_to_write)
    pdf_bytes = img2pdf.convert(image_name)

    buffer = io.BytesIO(pdf_bytes)
    os.remove(image_name)
    event_logger.info('Image Redaction Completed...')

    return redacted_count, PyPDF2.PdfFileReader(buffer)
