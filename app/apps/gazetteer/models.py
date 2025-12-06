from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Dynasty(models.Model):
    """朝代"""
    name = models.CharField(_('朝代名称'), max_length=100)
    start_year = models.IntegerField(_('起始年'), null=True, blank=True)
    end_year = models.IntegerField(_('结束年'), null=True, blank=True)
    description = models.TextField(_('描述'), blank=True)

    class Meta:
        verbose_name = _('朝代')
        verbose_name_plural = _('朝代')
        ordering = ['start_year']

    def __str__(self):
        return self.name

class Location(models.Model):
    """地理位置"""
    historical_name = models.CharField(_('历史地名'), max_length=255)
    modern_name = models.CharField(_('现代地名'), max_length=255, blank=True)
    admin_code = models.CharField(_('行政区划代码'), max_length=100, blank=True)
    latitude = models.DecimalField(_('纬度'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_('经度'), max_digits=9, decimal_places=6, null=True, blank=True)
    parent = models.ForeignKey('self', verbose_name=_('上级行政区'), 
                             on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='children')
    
    class Meta:
        verbose_name = _('地理位置')
        verbose_name_plural = _('地理位置')
        
    def __str__(self):
        return f"{self.historical_name} ({self.modern_name})" if self.modern_name else self.historical_name

class Gazetteer(models.Model):
    """方志"""
    title = models.CharField(_('志书名称'), max_length=255)
    dynasty = models.ForeignKey(Dynasty, verbose_name=_('朝代'),
                              on_delete=models.SET_NULL, null=True)
    year = models.IntegerField(_('修志年份'), null=True, blank=True)
    compiler = models.CharField(_('修志人'), max_length=255, blank=True)
    location = models.ForeignKey(Location, verbose_name=_('地点'),
                               on_delete=models.SET_NULL, null=True)
    description = models.TextField(_('描述'), blank=True)
    full_text = models.TextField(_('全文'), blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('方志')
        verbose_name_plural = _('方志')
        ordering = ['dynasty', 'year']
        
    def __str__(self):
        return self.title

class Category(models.Model):
    """分类"""
    name = models.CharField(_('分类名称'), max_length=100)
    parent = models.ForeignKey('self', verbose_name=_('父分类'),
                             on_delete=models.CASCADE, null=True, blank=True,
                             related_name='children')
    description = models.TextField(_('描述'), blank=True)
    
    class Meta:
        verbose_name = _('分类')
        verbose_name_plural = _('分类')
        
    def __str__(self):
        return self.name

class Entry(models.Model):
    """知识条目"""
    gazetteer = models.ForeignKey(Gazetteer, verbose_name=_('方志'),
                                 on_delete=models.CASCADE,
                                 related_name='entries')
    category = models.ForeignKey(Category, verbose_name=_('分类'),
                               on_delete=models.SET_NULL, null=True)
    title = models.CharField(_('条目标题'), max_length=255)
    content = models.TextField(_('条目内容'))
    source_page = models.IntegerField(_('原书页码'), null=True, blank=True)
    confidence = models.DecimalField(_('OCR可信度'), max_digits=5, decimal_places=2,
                                   null=True, blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('知识条目')
        verbose_name_plural = _('知识条目')
        
    def __str__(self):
        return self.title

class Entity(models.Model):
    """实体"""
    TYPE_CHOICES = (
        ('person', _('人物')),
        ('place', _('地点')),
        ('event', _('事件')),
        ('org', _('机构')),
        ('other', _('其他')),
    )
    
    name = models.CharField(_('实体名称'), max_length=255)
    type = models.CharField(_('实体类型'), max_length=50, choices=TYPE_CHOICES)
    description = models.TextField(_('描述'), blank=True)
    entries = models.ManyToManyField(Entry, verbose_name=_('相关条目'),
                                   related_name='entities')
    
    class Meta:
        verbose_name = _('实体')
        verbose_name_plural = _('实体')
        
    def __str__(self):
        return self.name

class EntityRelation(models.Model):
    """实体关系"""
    RELATION_TYPES = (
        ('located_in', _('位于')),
        ('part_of', _('属于')),
        ('related_to', _('相关')),
        ('ancestor_of', _('祖先')),
        ('successor_of', _('继任')),
    )
    
    source = models.ForeignKey(Entity, verbose_name=_('源实体'),
                             on_delete=models.CASCADE,
                             related_name='relations_from')
    target = models.ForeignKey(Entity, verbose_name=_('目标实体'),
                             on_delete=models.CASCADE,
                             related_name='relations_to')
    relation_type = models.CharField(_('关系类型'), max_length=50,
                                   choices=RELATION_TYPES)
    description = models.TextField(_('描述'), blank=True)
    
    class Meta:
        verbose_name = _('实体关系')
        verbose_name_plural = _('实体关系')
        
    def __str__(self):
        return f"{self.source} - {self.get_relation_type_display()} - {self.target}"