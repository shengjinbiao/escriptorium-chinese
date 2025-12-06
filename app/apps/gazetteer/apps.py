from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class GazetteerConfig(AppConfig):
    name = 'apps.gazetteer'
    verbose_name = _('地方志知识库')