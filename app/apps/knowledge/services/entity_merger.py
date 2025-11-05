"""
HanLP实体标注结果合并模块
"""
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from knowledge.services.entity_extraction import EntitySpan


@dataclass
class MergedEntity:
    """合并后的实体"""
    text: str
    type: str
    start: int
    end: int
    confidence: float
    source_model: str


class EntityMerger:
    """
    HanLP三个模型的实体标注结果合并器
    
    策略：
    1. 根据实体重叠度判断是否为同一实体
    2. 基于置信度和模型优先级选择最佳结果
    3. 统一实体类型映射
    """
    
    # 模型优先级（置信度相近时优先采用优先级高的模型结果）
    MODEL_PRIORITIES = {
        "OntoNotes": 3,
        "MSRA": 2, 
        "CTB": 1
    }
    
    # 实体类型映射到统一标准
    TYPE_MAPPING = {
        # OntoNotes
        "PERSON": "PERSON",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "ORG": "ORGANIZATION",
        "DATE": "TIME",
        "TIME": "TIME",
        # MSRA
        "PER": "PERSON",
        "LOC": "LOCATION",
        "ORG": "ORGANIZATION",
        # CTB
        "NR": "PERSON",
        "NS": "LOCATION",
        "NT": "ORGANIZATION",
    }
    
    def __init__(self, overlap_threshold: float = 0.8, confidence_threshold: float = 0.75):
        self.overlap_threshold = overlap_threshold
        self.confidence_threshold = confidence_threshold
    
    def _calculate_overlap(self, span1: "EntitySpan", span2: "EntitySpan") -> float:
        """计算两个实体span的重叠度"""
        start = max(span1.start, span2.start)
        end = min(span1.end, span2.end)
        if start >= end:
            return 0.0
        
        overlap_length = end - start
        span1_length = span1.end - span1.start
        span2_length = span2.end - span2.start
        
        return overlap_length / max(span1_length, span2_length)
    
    def _get_unified_type(self, entity_type: str) -> str:
        """获取统一的实体类型"""
        return self.TYPE_MAPPING.get(entity_type, entity_type or "OTHER")
    
    def _merge_overlapping_entities(self, entities: List[tuple["EntitySpan", str, float]]) -> List[MergedEntity]:
        """合并重叠的实体"""
        if not entities:
            return []
            
        # 按开始位置排序
        sorted_entities = sorted(entities, key=lambda x: (x[0].start, x[0].end))
        merged = []
        current_group = [sorted_entities[0]]
        
        for entity in sorted_entities[1:]:
            last_entity = current_group[-1][0]
            if self._calculate_overlap(last_entity, entity[0]) > self.overlap_threshold:
                current_group.append(entity)
            else:
                # 处理当前组
                if len(current_group) == 1:
                    e, model, conf = current_group[0]
                    if conf >= self.confidence_threshold:
                        merged.append(MergedEntity(
                            text=e.text,
                            type=self._get_unified_type(e.type),
                            start=e.start,
                            end=e.end,
                            confidence=conf,
                            source_model=model
                        ))
                else:
                    # 选择置信度最高的实体
                    best_entity = max(current_group, 
                                    key=lambda x: x[2] + self.MODEL_PRIORITIES[x[1]] * 0.1)
                    if best_entity[2] >= self.confidence_threshold:
                        e = best_entity[0]
                        merged.append(MergedEntity(
                            text=e.text,
                            type=self._get_unified_type(e.type),
                            start=e.start,
                            end=e.end,
                            confidence=best_entity[2],
                            source_model=best_entity[1]
                        ))
                current_group = [entity]
        
        # 处理最后一组
        if len(current_group) == 1:
            e, model, conf = current_group[0]
            if conf >= self.confidence_threshold:
                merged.append(MergedEntity(
                    text=e.text,
                    type=self._get_unified_type(e.type),
                    start=e.start,
                    end=e.end,
                    confidence=conf,
                    source_model=model
                ))
        elif len(current_group) > 1:
            best_entity = max(current_group,
                            key=lambda x: x[2] + self.MODEL_PRIORITIES[x[1]] * 0.1)
            if best_entity[2] >= self.confidence_threshold:
                e = best_entity[0]
                merged.append(MergedEntity(
                    text=e.text,
                    type=self._get_unified_type(e.type),
                    start=e.start,
                    end=e.end,
                    confidence=best_entity[2],
                    source_model=best_entity[1]
                ))
        
        return merged
    
    def merge_results(
        self,
        ontonotes_results: List["EntitySpan"],
        msra_results: List["EntitySpan"],
        ctb_results: List["EntitySpan"],
    ) -> List[MergedEntity]:
        """
        合并三个模型的实体识别结果
        
        Args:
            ontonotes_results: OntoNotes模型的结果
            msra_results: MSRA模型的结果
            ctb_results: CTB模型的结果
            
        Returns:
            合并后的实体列表
        """
        # 收集所有实体结果
        all_entities = []
        
        for entity in ontonotes_results:
            all_entities.append((entity, "OntoNotes", entity.confidence))
        
        for entity in msra_results:
            all_entities.append((entity, "MSRA", entity.confidence))
            
        for entity in ctb_results:
            all_entities.append((entity, "CTB", entity.confidence))
            
        # 合并重叠实体
        return self._merge_overlapping_entities(all_entities)
