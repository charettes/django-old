from django.db import models


class People(models.Model):
    name = models.CharField(max_length=255)

class Message(models.Model):
    from_field = models.ForeignKey(People, db_column='from_id')

class PeopleData(models.Model):
    people_pk = models.ForeignKey(People, primary_key=True)
    ssn = models.CharField(max_length=11)

class PeopleMoreData(models.Model):
    people_unique = models.ForeignKey(People, unique=True)
    license = models.CharField(max_length=255)

