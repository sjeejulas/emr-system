from django.db import models
from django.contrib.postgres.fields import ArrayField
from postgres_copy import CopyManager

from typing import Set


class SnomedConcept(models.Model):
    external_id = models.BigIntegerField(unique=True, primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    file_path = models.CharField(max_length=255)
    fsn_description = models.CharField(max_length=255)
    children = models.ManyToManyField(
        'self', through='SnomedDescendant', symmetrical=False,
        through_fields=('external_id', 'descendant_external_id')
    )
    external_fsn_description_id = models.BigIntegerField()
    objects = CopyManager()

    def __str__(self):
        return "{} - {}".format(self.external_id, self.fsn_description)

    class Meta:
        indexes = [
            models.Index(fields=['fsn_description']),
            models.Index(fields=['external_id']),
        ]
        default_related_name = 'snomed_concepts'

    # Todo have to fixed performance
    def descendants(self, include_self=True, ret_descendants=set()) -> Set['SnomedConcept']:
        if self not in ret_descendants:
            if include_self:
                ret_descendants.add(self)
            for child in self.children.all():
                if child not in ret_descendants:
                    child.descendants(include_self=True, ret_descendants=ret_descendants)
        return ret_descendants

    def descendant_readcodes(self, snome_descendants: Set['SnomedConcept']=None) -> Set['ReadCode']:
        """
        Return readcodes of this snomed concept and its descendants.
        """
        descendants_readcodes = set()
        if not snome_descendants:
            snome_descendants = self.descendants(ret_descendants=set())
        for sc in snome_descendants:
            for r in sc.readcode.all():
                descendants_readcodes.add(r)
        return descendants_readcodes

    def is_descendant_of(self, snomed_concept: 'SnomedConcept') -> bool:
        return self in snomed_concept.descendants(ret_descendants=set())


class ReadCode(models.Model):
    ext_read_code = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    file_path = models.CharField(max_length=255)
    concept_id = models.ForeignKey(
        SnomedConcept, to_field='external_id', on_delete=models.CASCADE, db_column="concept_id", null=True,
        related_name='readcode'
    )
    objects = CopyManager()

    def __str__(self):
        return "{} - {}".format(self.id, self.ext_read_code)

    def is_descendant_of_snomed_concept(self, snomed_concept: SnomedConcept) -> bool:
        return self in snomed_concept.descendant_readcodes()

    def related_snomed_concepts_and_descendants(self) -> Set[SnomedConcept]:
        """
        Return snomed concepts with a FK to this readcode and all of their
        descendants.
        """
        snomed_concepts = set()
        snomed_concepts.update(self.concept_id.descendants(ret_descendants=set()))
        return snomed_concepts


class SnomedDescendant(models.Model):
    descendant_external_id = models.ForeignKey(SnomedConcept, to_field='external_id', on_delete=models.CASCADE,
                                               db_column="descendant_external_id", null=True, related_name='descendant_external_id')
    external_id = models.ForeignKey(SnomedConcept, to_field='external_id', on_delete=models.CASCADE,
                                    db_column="external_id", null=True, related_name='external_ids')
    objects = CopyManager()

    def __str__(self):
        return "{} - {} - {}".format(self.id, self.descendant_external_id.fsn_description, self.external_id)

    class Meta:
        indexes = [
            models.Index(fields=['external_id']),
        ]


class CommonSnomedConcepts(models.Model):
    common_name = models.CharField(max_length=255)
    snomed_concept_code = models.ManyToManyField(SnomedConcept)
    descendant_snomed_id = ArrayField(models.BigIntegerField(), null=True, default=list)
    descendant_readcodes = ArrayField(models.CharField(max_length=255), null=True, default=list)

    def __str__(self):
        return self.common_name
