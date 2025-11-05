from django.core.management.base import BaseCommand
from apps.gazetteer.models import Dynasty, Location, Category, Gazetteer, Entry, Entity, EntityRelation

class Command(BaseCommand):
    help = '创建测试数据'

    def handle(self, *args, **kwargs):
        self.stdout.write('创建测试数据...')
        
        # 创建朝代
        self.stdout.write('创建朝代...')
        dynasties = {
            'ming': Dynasty.objects.create(
                name='明朝',
                start_year=1368,
                end_year=1644,
                description='明朝是中国历史上最后一个由汉族建立的大一统王朝'
            ),
            'qing': Dynasty.objects.create(
                name='清朝',
                start_year=1644,
                end_year=1912,
                description='中国历史上最后一个封建王朝'
            )
        }
        
        # 创建地点
        self.stdout.write('创建地点...')
        locations = {}
        # 先创建父级地点
        locations['jiangsu'] = Location.objects.create(
            historical_name='江南',
            modern_name='江苏',
            admin_code='320000'
        )
        locations['zhejiang'] = Location.objects.create(
            historical_name='浙江',
            modern_name='浙江',
            admin_code='330000'
        )
        
        # 再创建子级地点
        locations['suzhou'] = Location.objects.create(
            historical_name='姑苏',
            modern_name='苏州',
            admin_code='320500',
            parent=locations['jiangsu']
        )
        locations['hangzhou'] = Location.objects.create(
            historical_name='杭州',
            modern_name='杭州',
            admin_code='330100',
            parent=locations['zhejiang']
        )
        
        # 创建分类
        self.stdout.write('创建分类...')
        categories = {
            'geography': Category.objects.create(
                name='地理',
                description='地理位置、山川形势等'
            ),
            'history': Category.objects.create(
                name='历史沿革',
                description='建置沿革、历史变迁等'
            ),
            'culture': Category.objects.create(
                name='文化',
                description='风俗习惯、文化特色等'
            ),
            'economy': Category.objects.create(
                name='经济',
                description='物产、商贸等'
            ),
            'education': Category.objects.create(
                name='教育',
                description='学校、科举等'
            )
        }
        
        # 创建方志
        self.stdout.write('创建方志...')
        gazetteers = {
            'suzhou': Gazetteer.objects.create(
                title='姑苏志',
                dynasty=dynasties['ming'],
                year=1506,
                compiler='王鏊',
                location=locations['suzhou'],
                description='明正德年间修撰的姑苏府志'
            ),
            'hangzhou': Gazetteer.objects.create(
                title='杭州府志',
                dynasty=dynasties['qing'],
                year=1784,
                compiler='沈翼机',
                location=locations['hangzhou'],
                description='清乾隆年间修撰的杭州府志'
            )
        }
        
        # 创建条目
        self.stdout.write('创建条目...')
        entries = {
            'suzhou_geo': Entry.objects.create(
                gazetteer=gazetteers['suzhou'],
                category=categories['geography'],
                title='姑苏城池',
                content='姑苏城四面环水，周围六十里...',
                source_page=1
            ),
            'suzhou_culture': Entry.objects.create(
                gazetteer=gazetteers['suzhou'],
                category=categories['culture'],
                title='姑苏风俗',
                content='园林遍布，文人雅士众多...',
                source_page=15
            ),
            'hangzhou_geo': Entry.objects.create(
                gazetteer=gazetteers['hangzhou'],
                category=categories['geography'],
                title='钱塘江',
                content='钱塘江水势浩荡，潮水壮观...',
                source_page=3
            ),
            'hangzhou_culture': Entry.objects.create(
                gazetteer=gazetteers['hangzhou'],
                category=categories['culture'],
                title='西湖胜景',
                content='西湖十景，举世闻名...',
                source_page=20
            )
        }
        
        # 创建实体
        self.stdout.write('创建实体...')
        entities = {
            'wang_ao': Entity.objects.create(
                name='王鏊',
                type='person',
                description='明代著名文学家、政治家'
            ),
            'shen_yiji': Entity.objects.create(
                name='沈翼机',
                type='person',
                description='清代官员、学者'
            ),
            'suzhou_city': Entity.objects.create(
                name='姑苏城',
                type='place',
                description='历史文化名城'
            ),
            'west_lake': Entity.objects.create(
                name='西湖',
                type='place',
                description='著名风景区'
            ),
            'qiantang_river': Entity.objects.create(
                name='钱塘江',
                type='place',
                description='浙江省第一大河'
            )
        }
        
        # 添加实体与条目的关联
        entities['wang_ao'].entries.add(entries['suzhou_geo'], entries['suzhou_culture'])
        entities['shen_yiji'].entries.add(entries['hangzhou_geo'], entries['hangzhou_culture'])
        entities['suzhou_city'].entries.add(entries['suzhou_geo'])
        entities['west_lake'].entries.add(entries['hangzhou_culture'])
        entities['qiantang_river'].entries.add(entries['hangzhou_geo'])
        
        # 创建实体关系
        self.stdout.write('创建实体关系...')
        EntityRelation.objects.create(
            source=entities['wang_ao'],
            target=entities['suzhou_city'],
            relation_type='related_to',
            description='王鏊为姑苏城修志'
        )
        EntityRelation.objects.create(
            source=entities['shen_yiji'],
            target=entities['west_lake'],
            relation_type='related_to',
            description='沈翼机记录西湖胜景'
        )
        EntityRelation.objects.create(
            source=entities['west_lake'],
            target=entities['qiantang_river'],
            relation_type='located_in',
            description='西湖临近钱塘江'
        )
        
        self.stdout.write(self.style.SUCCESS('成功创建测试数据！'))