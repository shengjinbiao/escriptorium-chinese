<template>
    <div class="knowledge-graph">
        <div class="knowledge-graph__header">
            <h2>知识图谱</h2>
            <div class="knowledge-graph__filters">
                <div class="form-group">
                    <label>实体类型筛选</label>
                    <div class="type-filters">
                        <div v-for="type in entityTypes"
                             :key="type.value"
                             class="custom-control custom-checkbox">
                            <input type="checkbox"
                                   :id="'type-' + type.value"
                                   v-model="filters.types[type.value]"
                                   class="custom-control-input"
                                   @change="updateGraph">
                            <label class="custom-control-label"
                                   :for="'type-' + type.value">
                                {{ type.label }}
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>关系类型筛选</label>
                    <div class="relation-filters">
                        <div v-for="type in relationTypes"
                             :key="type.value"
                             class="custom-control custom-checkbox">
                            <input type="checkbox"
                                   :id="'relation-' + type.value"
                                   v-model="filters.relationTypes[type.value]"
                                   class="custom-control-input"
                                   @change="updateGraph">
                            <label class="custom-control-label"
                                   :for="'relation-' + type.value">
                                {{ type.label }}
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>搜索实体</label>
                    <div class="search-box">
                        <input type="text"
                               v-model="searchQuery"
                               class="form-control"
                               placeholder="输入实体名称..."
                               @input="searchEntities">
                    </div>
                </div>
                
                <div class="graph-controls">
                    <button class="btn btn-outline-primary"
                            @click="stabilizeGraph">
                        <i class="fas fa-compress-arrows-alt"></i>
                        重置布局
                    </button>
                    <button class="btn btn-outline-secondary"
                            @click="togglePhysics">
                        {{ physicsEnabled ? '禁用' : '启用' }}物理引擎
                    </button>
                </div>
            </div>
        </div>

        <div class="knowledge-graph__content">
            <!-- 图谱容器 -->
            <div class="graph-container" ref="graphContainer">
                <div v-if="loading" class="loading-overlay">
                    <div class="spinner-border" role="status">
                        <span class="sr-only">加载中...</span>
                    </div>
                </div>
            </div>
            
            <!-- 搜索结果弹出框 -->
            <div v-if="searchResults.length && showSearchResults"
                 class="search-results">
                <div class="search-results__header">
                    <h6>搜索结果</h6>
                    <button type="button" 
                            class="close"
                            @click="showSearchResults = false">
                        <span>&times;</span>
                    </button>
                </div>
                <div class="search-results__content">
                    <div v-for="entity in searchResults"
                         :key="entity.id"
                         class="search-result-item"
                         @click="focusEntity(entity)">
                        <span class="entity-name">{{ entity.name }}</span>
                        <span class="badge"
                              :class="getTypeClass(entity.type)">
                            {{ getTypeLabel(entity.type) }}
                        </span>
                    </div>
                </div>
            </div>
            
            <!-- 实体详情侧边栏 -->
            <div v-if="selectedEntity"
                 class="entity-sidebar">
                <div class="entity-sidebar__header">
                    <h5>{{ selectedEntity.name }}</h5>
                    <button type="button"
                            class="close"
                            @click="selectedEntity = null">
                        <span>&times;</span>
                    </button>
                </div>
                <div class="entity-sidebar__content">
                    <div class="entity-info">
                        <p class="entity-type">
                            <span class="badge"
                                  :class="getTypeClass(selectedEntity.type)">
                                {{ getTypeLabel(selectedEntity.type) }}
                            </span>
                        </p>
                        <p class="entity-description">
                            {{ selectedEntity.description || '暂无描述' }}
                        </p>
                        <div class="entity-meta">
                            <div class="meta-item">
                                <span class="meta-label">相关条目</span>
                              <span class="meta-value">
                                  {{ (selectedEntity && selectedEntity.entries) ? selectedEntity.entries.length : 0 }}
                              </span>
                            </div>
                            <div class="meta-item">
                                <span class="meta-label">关系数量</span>
                                <span class="meta-value">
                                    {{ getEntityRelationCount(selectedEntity.id) }}
                                </span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="entity-actions">
                        <router-link
                            :to="{ name: 'entity-detail', params: { id: selectedEntity.id }}"
                            class="btn btn-primary btn-block">
                            查看详情
                        </router-link>
                    </div>
                    
                    <!-- 相关实体 -->
                    <div class="related-entities">
                        <h6>相关实体</h6>
                        <div class="related-entity-list">
                            <div v-for="relation in getEntityRelations(selectedEntity.id)"
                                 :key="relation.id"
                                 class="related-entity-item"
                                 @click="focusRelatedEntity(relation)">
                                <span class="entity-name">
                                    {{ getRelatedEntityName(relation) }}
                                </span>
                                <span class="relation-type">
                                    {{ getRelationLabel(relation) }}
                                </span>
                            </div>
                            <div v-if="!getEntityRelations(selectedEntity.id).length"
                                 class="text-center py-2">
                                暂无相关实体
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import debounce from 'lodash/debounce';

export default {
    name: 'KnowledgeGraph',
    
    data() {
        return {
            loading: false,
            network: null,
            nodes: null,
            edges: null,
            allEntities: [],
            allRelations: [],
            selectedEntity: null,
            searchQuery: '',
            searchResults: [],
            showSearchResults: false,
            physicsEnabled: true,
            filters: {
                types: {
                    person: true,
                    place: true,
                    event: true,
                    org: true,
                    other: true
                },
                relationTypes: {
                    located_in: true,
                    part_of: true,
                    related_to: true,
                    ancestor_of: true,
                    successor_of: true
                }
            },
            entityTypes: [
                { value: 'person', label: '人物' },
                { value: 'place', label: '地点' },
                { value: 'event', label: '事件' },
                { value: 'org', label: '机构' },
                { value: 'other', label: '其他' }
            ],
            relationTypes: [
                { value: 'located_in', label: '位于' },
                { value: 'part_of', label: '属于' },
                { value: 'related_to', label: '相关' },
                { value: 'ancestor_of', label: '祖先' },
                { value: 'successor_of', label: '继任' }
            ]
        };
    },
    
    methods: {
        async loadData() {
            this.loading = true;
            try {
                // 加载所有实体
                const entitiesResponse = await fetch('/api/gazetteer/entities/');
                if (!entitiesResponse.ok) throw new Error('加载实体失败');
                this.allEntities = await entitiesResponse.json();
                
                // 加载所有关系
                const relationsResponse = await fetch('/api/gazetteer/relations/');
                if (!relationsResponse.ok) throw new Error('加载关系失败');
                this.allRelations = await relationsResponse.json();
                
                this.initGraph();
            } catch (error) {
                console.error('加载数据失败:', error);
            } finally {
                this.loading = false;
            }
        },
        
        initGraph() {
            // 创建数据集
            this.nodes = new DataSet();
            this.edges = new DataSet();
            
            // 添加节点
            this.allEntities.forEach(entity => {
                if (this.filters.types[entity.type]) {
                    this.nodes.add({
                        id: entity.id,
                        label: entity.name,
                        group: entity.type,
                        title: entity.description || entity.name,
                        value: this.getEntityRelationCount(entity.id)
                    });
                }
            });
            
            // 添加边
            this.allRelations.forEach(relation => {
                if (this.filters.relationTypes[relation.relation_type]) {
                    this.edges.add({
                        id: relation.id,
                        from: relation.source.id,
                        to: relation.target.id,
                        label: this.relationTypes.find(t => t.value === relation.relation_type)?.label,
                        arrows: 'to',
                        title: relation.description || ''
                    });
                }
            });
            
            // 配置选项
            const options = {
                nodes: {
                    shape: 'dot',
                    scaling: {
                        min: 10,
                        max: 30,
                        label: {
                            min: 8,
                            max: 16
                        }
                    },
                    font: {
                        size: 12,
                        face: 'Arial'
                    }
                },
                edges: {
                    font: {
                        size: 8,
                        align: 'middle'
                    },
                    color: { inherit: 'both' },
                    smooth: {
                        type: 'continuous'
                    }
                },
                physics: {
                    enabled: this.physicsEnabled,
                    barnesHut: {
                        gravitationalConstant: -2000,
                        centralGravity: 0.3,
                        springLength: 95,
                        springConstant: 0.04,
                        damping: 0.09
                    }
                },
                groups: {
                    person: { color: { background: '#007bff', border: '#0056b3' } },
                    place: { color: { background: '#28a745', border: '#145523' } },
                    event: { color: { background: '#ffc107', border: '#d39e00' } },
                    org: { color: { background: '#17a2b8', border: '#0f6674' } },
                    other: { color: { background: '#6c757d', border: '#494f54' } }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200,
                    zoomView: true
                }
            };
            
            // 创建网络
            this.network = new Network(
                this.$refs.graphContainer,
                { nodes: this.nodes, edges: this.edges },
                options
            );
            
            // 事件监听
            this.network.on('selectNode', (params) => {
                if (params.nodes.length) {
                    const nodeId = params.nodes[0];
                    const entity = this.allEntities.find(e => e.id === nodeId);
                    if (entity) {
                        this.selectedEntity = entity;
                    }
                }
            });
            
            this.network.on('deselectNode', () => {
                // 点击空白处时，如果不是在侧边栏内点击，则清除选中状态
                if (!this.clickInSidebar) {
                    this.selectedEntity = null;
                }
            });
        },
        
        updateGraph() {
            if (!this.network) return;
            
            // 更新节点
            const nodesToUpdate = this.allEntities
                .filter(entity => this.filters.types[entity.type])
                .map(entity => ({
                    id: entity.id,
                    label: entity.name,
                    group: entity.type,
                    title: entity.description || entity.name,
                    value: this.getEntityRelationCount(entity.id)
                }));
            
            // 更新边
            const edgesToUpdate = this.allRelations
                .filter(relation => this.filters.relationTypes[relation.relation_type])
                .map(relation => ({
                    id: relation.id,
                    from: relation.source.id,
                    to: relation.target.id,
                    label: this.relationTypes.find(t => t.value === relation.relation_type)?.label,
                    arrows: 'to',
                    title: relation.description || ''
                }));
            
            this.nodes.clear();
            this.edges.clear();
            this.nodes.add(nodesToUpdate);
            this.edges.add(edgesToUpdate);
        },
        
        getTypeLabel(type) {
            return this.entityTypes.find(t => t.value === type)?.label || type;
        },
        
        getTypeClass(type) {
            const classes = {
                person: 'badge-primary',
                place: 'badge-success',
                event: 'badge-warning',
                org: 'badge-info',
                other: 'badge-secondary'
            };
            return classes[type] || 'badge-secondary';
        },
        
        getRelationLabel(relation) {
            const type = this.relationTypes.find(t => t.value === relation.relation_type)?.label;
            if (!type) return '';
            return relation.source.id === this.selectedEntity.id
                ? `→ ${type}`
                : `← ${type}`;
        },
        
        getEntityRelationCount(entityId) {
            return this.allRelations.filter(
                r => r.source.id === entityId || r.target.id === entityId
            ).length;
        },
        
        getEntityRelations(entityId) {
            return this.allRelations.filter(
                r => r.source.id === entityId || r.target.id === entityId
            );
        },
        
        getRelatedEntityName(relation) {
            return relation.source.id === this.selectedEntity.id
                ? relation.target.name
                : relation.source.name;
        },
        
        focusEntity(entity) {
            this.network.focus(entity.id, {
                scale: 1.5,
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
            this.network.selectNodes([entity.id]);
            this.selectedEntity = entity;
            this.showSearchResults = false;
        },
        
        focusRelatedEntity(relation) {
            const relatedEntityId = relation.source.id === this.selectedEntity.id
                ? relation.target.id
                : relation.source.id;
            const relatedEntity = this.allEntities.find(e => e.id === relatedEntityId);
            if (relatedEntity) {
                this.focusEntity(relatedEntity);
            }
        },
        
        stabilizeGraph() {
            this.network.stabilize();
        },
        
        togglePhysics() {
            this.physicsEnabled = !this.physicsEnabled;
            this.network.setOptions({ physics: { enabled: this.physicsEnabled } });
        },
        
        searchEntities: debounce(function() {
            if (!this.searchQuery) {
                this.searchResults = [];
                this.showSearchResults = false;
                return;
            }
            
            const query = this.searchQuery.toLowerCase();
            this.searchResults = this.allEntities.filter(entity =>
                entity.name.toLowerCase().includes(query) ||
                (entity.description || '').toLowerCase().includes(query)
            );
            this.showSearchResults = true;
        }, 300)
    },
    
    async created() {
        await this.loadData();
    },
    
    beforeDestroy() {
        if (this.network) {
            this.network.destroy();
        }
    }
};
</script>

<style lang="scss" scoped>
.knowledge-graph {
    display: flex;
    flex-direction: column;
    height: 100vh;
    
    &__header {
        padding: 1rem;
        background-color: white;
        border-bottom: 1px solid #e5e7eb;
        
        h2 {
            margin-bottom: 1rem;
        }
    }
    
    &__filters {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        
        .type-filters,
        .relation-filters {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        
        .graph-controls {
            display: flex;
            gap: 0.5rem;
        }
    }
    
    &__content {
        flex: 1;
        position: relative;
        overflow: hidden;
        
        .graph-container {
            width: 100%;
            height: 100%;
        }
        
        .loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
        }
    }
    
    .search-results {
        position: absolute;
        top: 1rem;
        left: 1rem;
        width: 300px;
        background: white;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        
        &__header {
            padding: 0.75rem;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
            
            h6 {
                margin: 0;
            }
        }
        
        &__content {
            max-height: 300px;
            overflow-y: auto;
            
            .search-result-item {
                padding: 0.5rem 0.75rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: pointer;
                
                &:hover {
                    background-color: #f8f9fa;
                }
                
                .badge {
                    font-size: 0.75rem;
                }
            }
        }
    }
    
    .entity-sidebar {
        position: absolute;
        top: 0;
        right: 0;
        width: 300px;
        height: 100%;
        background: white;
        border-left: 1px solid #e5e7eb;
        display: flex;
        flex-direction: column;
        
        &__header {
            padding: 1rem;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
            
            h5 {
                margin: 0;
            }
        }
        
        &__content {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            
            .entity-info {
                margin-bottom: 1rem;
                
                .entity-type {
                    margin-bottom: 0.5rem;
                    
                    .badge {
                        font-size: 0.875rem;
                        padding: 0.4em 0.6em;
                    }
                }
                
                .entity-description {
                    color: #4b5563;
                    margin-bottom: 1rem;
                }
                
                .entity-meta {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 1rem;
                    
                    .meta-item {
                        text-align: center;
                        
                        .meta-label {
                            font-size: 0.75rem;
                            color: #6b7280;
                            margin-bottom: 0.25rem;
                        }
                        
                        .meta-value {
                            font-size: 1.25rem;
                            font-weight: 600;
                        }
                    }
                }
            }
            
            .entity-actions {
                margin-bottom: 1rem;
            }
            
            .related-entities {
                h6 {
                    margin-bottom: 0.75rem;
                }
                
                .related-entity-item {
                    padding: 0.5rem;
                    cursor: pointer;
                    border-radius: 4px;
                    
                    &:hover {
                        background-color: #f8f9fa;
                    }
                    
                    .entity-name {
                        display: block;
                        margin-bottom: 0.25rem;
                    }
                    
                    .relation-type {
                        font-size: 0.75rem;
                        color: #6b7280;
                    }
                }
            }
        }
    }
}

// 自定义复选框样式
.custom-checkbox {
    .custom-control-input:checked ~ .custom-control-label::before {
        border-color: #007bff;
        background-color: #007bff;
    }
}
</style>
