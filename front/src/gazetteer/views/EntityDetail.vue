<template>
    <div class="entity-detail" v-if="entity">
        <div class="entity-detail__header">
            <h2>{{ entity.name }}</h2>
            <span class="badge"
                  :class="getTypeClass(entity.type)">
                {{ getTypeLabel(entity.type) }}
            </span>
        </div>

        <div class="entity-detail__content">
            <div class="row">
                <!-- 左侧信息 -->
                <div class="col-md-4">
                    <div class="card mb-4">
                        <div class="card-body">
                            <h5 class="card-title">基本信息</h5>
                            <div class="entity-info">
                                <p class="entity-info__description">
                                    {{ entity.description || '暂无描述' }}
                                </p>
                                <div class="entity-info__meta">
                                    <div class="meta-item">
                                        <span class="meta-label">相关条目</span>
                                        <span class="meta-value">{{ entity.entries.length }}</span>
                                    </div>
                                    <div class="meta-item">
                                        <span class="meta-label">关系数量</span>
                                        <span class="meta-value">{{ relations.length }}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="entity-actions mt-3">
                                <button class="btn btn-sm btn-outline-primary"
                                        @click="editEntity">
                                    编辑信息
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- 关系列表 -->
                    <div class="card mb-4">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="card-title mb-0">实体关系</h5>
                                <button class="btn btn-sm btn-outline-primary"
                                        @click="showAddRelationDialog">
                                    添加关系
                                </button>
                            </div>
                            <div class="relation-list">
                                <div v-for="relation in relations"
                                     :key="relation.id"
                                     class="relation-item">
                                    <div class="relation-content">
                                        <router-link
                                            :to="{ 
                                                name: 'entity-detail',
                                                params: { 
                                                    id: relation.source.id === entity.id 
                                                        ? relation.target.id 
                                                        : relation.source.id
                                                }
                                            }"
                                            class="relation-entity">
                                            {{ relation.source.id === entity.id 
                                                ? relation.target.name 
                                                : relation.source.name }}
                                        </router-link>
                                        <span class="relation-type">
                                            {{ getRelationLabel(relation) }}
                                        </span>
                                    </div>
                                    <button class="btn btn-sm btn-link text-danger"
                                            @click="deleteRelation(relation)">
                                        删除
                                    </button>
                                </div>
                                <div v-if="!relations.length"
                                     class="text-center py-3">
                                    暂无关系数据
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 右侧内容 -->
                <div class="col-md-8">
                    <!-- 关系图谱 -->
                    <div class="card mb-4">
                        <div class="card-body">
                            <h5 class="card-title">关系图谱</h5>
                            <div class="relation-graph"
                                 ref="graphContainer"
                                 style="height: 400px;">
                            </div>
                        </div>
                    </div>

                    <!-- 相关条目 -->
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">相关条目</h5>
                            <div class="entry-list">
                                <div v-for="entry in entity.entries"
                                     :key="entry.id"
                                     class="entry-item">
                                    <div class="entry-header">
                                        <h6>{{ entry.title }}</h6>
                                        <div class="entry-meta">
                                            <span class="badge badge-info">
                                                {{ entry.category_name }}
                                            </span>
                                            <span v-if="entry.gazetteer_title"
                                                  class="text-muted ml-2">
                                                {{ entry.gazetteer_title }}
                                            </span>
                                        </div>
                                    </div>
                                    <p class="entry-content">
                                        {{ truncate(entry.content, 200) }}
                                    </p>
                                    <div class="entry-footer">
                                        <router-link
                                            :to="{ name: 'gazetteer-detail', params: { id: entry.gazetteer }}"
                                            class="btn btn-sm btn-link">
                                            查看原文
                                        </router-link>
                                    </div>
                                </div>
                                <div v-if="!entity.entries.length"
                                     class="text-center py-3">
                                    暂无相关条目
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 编辑实体对话框 -->
        <div v-if="showEntityDialog" class="modal fade show" style="display: block;">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">编辑实体</h5>
                        <button type="button" class="close" @click="closeEntityDialog">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <form @submit.prevent="saveEntity">
                            <div class="form-group">
                                <label>名称</label>
                                <input type="text"
                                       v-model="entityForm.name"
                                       class="form-control"
                                       required>
                            </div>
                            <div class="form-group">
                                <label>类型</label>
                                <select v-model="entityForm.type"
                                        class="form-control"
                                        required>
                                    <option v-for="type in entityTypes"
                                            :key="type.value"
                                            :value="type.value">
                                        {{ type.label }}
                                    </option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>描述</label>
                                <textarea v-model="entityForm.description"
                                          class="form-control"
                                          rows="3"></textarea>
                            </div>
                            <div class="text-right">
                                <button type="button"
                                        class="btn btn-secondary mr-2"
                                        @click="closeEntityDialog">
                                    取消
                                </button>
                                <button type="submit" class="btn btn-primary">
                                    保存
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- 添加关系对话框 -->
        <div v-if="showRelationDialog" class="modal fade show" style="display: block;">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">添加关系</h5>
                        <button type="button" class="close" @click="closeRelationDialog">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <form @submit.prevent="saveRelation">
                            <div class="form-group">
                                <label>关系类型</label>
                                <select v-model="relationForm.type"
                                        class="form-control"
                                        required>
                                    <option value="">请选择关系类型</option>
                                    <option v-for="type in relationTypes"
                                            :key="type.value"
                                            :value="type.value">
                                        {{ type.label }}
                                    </option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>目标实体</label>
                                <input type="text"
                                       v-model="targetEntitySearch"
                                       class="form-control"
                                       placeholder="搜索实体..."
                                       @input="searchTargetEntities">
                                <div v-if="searchResults.length"
                                     class="entity-search-results">
                                    <div v-for="result in searchResults"
                                         :key="result.id"
                                         class="entity-search-item"
                                         @click="selectTargetEntity(result)">
                                        <span>{{ result.name }}</span>
                                        <small>{{ getTypeLabel(result.type) }}</small>
                                    </div>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>描述</label>
                                <textarea v-model="relationForm.description"
                                          class="form-control"
                                          rows="3"></textarea>
                            </div>
                            <div class="text-right">
                                <button type="button"
                                        class="btn btn-secondary mr-2"
                                        @click="closeRelationDialog">
                                    取消
                                </button>
                                <button type="submit"
                                        class="btn btn-primary"
                                        :disabled="!relationForm.target_id">
                                    保存
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

export default {
    name: 'EntityDetail',
    
    props: {
        id: {
            type: [Number, String],
            required: true
        }
    },
    
    data() {
        return {
            relations: [],
            showEntityDialog: false,
            showRelationDialog: false,
            entityForm: this.getEmptyEntityForm(),
            relationForm: this.getEmptyRelationForm(),
            targetEntitySearch: '',
            searchResults: [],
            network: null,
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
    
    computed: {
        ...mapState({
            entity: state => state.currentEntity,
            loading: state => state.loading,
            error: state => state.error
        })
    },
    
    methods: {
        ...mapActions(['fetchEntity']),
        
        getEmptyEntityForm() {
            return {
                name: '',
                type: '',
                description: ''
            };
        },
        
        getEmptyRelationForm() {
            return {
                type: '',
                target_id: null,
                description: ''
            };
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
            return relation.source.id === this.entity.id
                ? `→ ${type}`
                : `← ${type}`;
        },
        
        async loadRelations() {
            try {
                const response = await fetch(`/api/gazetteer/entities/${this.id}/relations/`);
                if (!response.ok) throw new Error('加载关系失败');
                this.relations = await response.json();
                this.initGraph();
            } catch (error) {
                console.error('加载关系失败:', error);
            }
        },
        
        initGraph() {
            if (!this.$refs.graphContainer) return;
            
            // 准备数据
            const nodes = new DataSet();
            const edges = new DataSet();
            
            // 添加中心节点
            nodes.add({
                id: this.entity.id,
                label: this.entity.name,
                group: this.entity.type,
                size: 25
            });
            
            // 添加关联节点和边
            this.relations.forEach(relation => {
                const otherEntity = relation.source.id === this.entity.id
                    ? relation.target
                    : relation.source;
                    
                nodes.add({
                    id: otherEntity.id,
                    label: otherEntity.name,
                    group: otherEntity.type,
                    size: 20
                });
                
                edges.add({
                    from: relation.source.id,
                    to: relation.target.id,
                    label: this.relationTypes.find(t => t.value === relation.relation_type)?.label,
                    arrows: relation.source.id === this.entity.id ? 'to' : 'from'
                });
            });
            
            // 配置选项
            const options = {
                nodes: {
                    shape: 'dot',
                    font: {
                        size: 14
                    }
                },
                edges: {
                    font: {
                        size: 12
                    },
                    width: 2
                },
                groups: {
                    person: { color: '#007bff' },
                    place: { color: '#28a745' },
                    event: { color: '#ffc107' },
                    org: { color: '#17a2b8' },
                    other: { color: '#6c757d' }
                },
                physics: {
                    stabilization: false,
                    barnesHut: {
                        gravitationalConstant: -2000,
                        springConstant: 0.04
                    }
                }
            };
            
            // 创建网络
            this.network = new Network(
                this.$refs.graphContainer,
                { nodes, edges },
                options
            );
            
            // 点击事件
            this.network.on('click', (params) => {
                if (params.nodes.length) {
                    const nodeId = params.nodes[0];
                    if (nodeId !== this.entity.id) {
                        this.$router.push({
                            name: 'entity-detail',
                            params: { id: nodeId }
                        });
                    }
                }
            });
        },
        
        editEntity() {
            this.entityForm = {
                name: this.entity.name,
                type: this.entity.type,
                description: this.entity.description
            };
            this.showEntityDialog = true;
        },
        
        async saveEntity() {
            try {
                const response = await fetch(`/api/gazetteer/entities/${this.id}/`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify(this.entityForm)
                });
                
                if (!response.ok) throw new Error('保存失败');
                
                await this.fetchEntity(this.id);
                this.closeEntityDialog();
                
            } catch (error) {
                console.error('保存实体失败:', error);
            }
        },
        
        closeEntityDialog() {
            this.showEntityDialog = false;
            this.entityForm = this.getEmptyEntityForm();
        },
        
        showAddRelationDialog() {
            this.showRelationDialog = true;
        },
        
        async searchTargetEntities() {
            if (!this.targetEntitySearch) {
                this.searchResults = [];
                return;
            }
            
            try {
                const response = await fetch(
                    `/api/gazetteer/entities/?search=${this.targetEntitySearch}`
                );
                if (!response.ok) throw new Error('搜索失败');
                const results = await response.json();
                this.searchResults = results.filter(e => e.id !== this.entity.id);
            } catch (error) {
                console.error('搜索实体失败:', error);
            }
        },
        
        selectTargetEntity(entity) {
            this.relationForm.target_id = entity.id;
            this.targetEntitySearch = entity.name;
            this.searchResults = [];
        },
        
        async saveRelation() {
            try {
                const response = await fetch('/api/gazetteer/relations/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        source: this.id,
                        target: this.relationForm.target_id,
                        relation_type: this.relationForm.type,
                        description: this.relationForm.description
                    })
                });
                
                if (!response.ok) throw new Error('保存失败');
                
                await this.loadRelations();
                this.closeRelationDialog();
                
            } catch (error) {
                console.error('保存关系失败:', error);
            }
        },
        
        closeRelationDialog() {
            this.showRelationDialog = false;
            this.relationForm = this.getEmptyRelationForm();
            this.targetEntitySearch = '';
            this.searchResults = [];
        },
        
        async deleteRelation(relation) {
            if (!confirm('确定要删除这个关系吗？')) return;
            
            try {
                const response = await fetch(`/api/gazetteer/relations/${relation.id}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });
                
                if (!response.ok) throw new Error('删除失败');
                
                await this.loadRelations();
                
            } catch (error) {
                console.error('删除关系失败:', error);
            }
        },
        
        truncate(text, length = 100) {
            if (!text) return '';
            return text.length > length
                ? text.slice(0, length) + '...'
                : text;
        }
    },
    
    async created() {
        await this.fetchEntity(this.id);
        await this.loadRelations();
    },
    
    mounted() {
        this.$nextTick(() => {
            this.initGraph();
        });
    },
    
    beforeDestroy() {
        if (this.network) {
            this.network.destroy();
        }
    },
    
    watch: {
        id: {
            async handler(newId) {
                await this.fetchEntity(newId);
                await this.loadRelations();
            }
        }
    }
};
</script>

<style lang="scss" scoped>
.entity-detail {
    padding: 2rem;
    
    &__header {
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        
        h2 {
            margin: 0;
        }
        
        .badge {
            padding: 0.5em 0.7em;
            font-size: 1rem;
        }
    }
    
    .entity-info {
        &__description {
            margin-bottom: 1rem;
            line-height: 1.6;
        }
        
        &__meta {
            display: flex;
            gap: 1rem;
            
            .meta-item {
                display: flex;
                flex-direction: column;
                
                .meta-label {
                    font-size: 0.875rem;
                    color: #6c757d;
                }
                
                .meta-value {
                    font-size: 1.25rem;
                    font-weight: 600;
                }
            }
        }
    }
    
    .relation-list {
        .relation-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #e9ecef;
            
            &:last-child {
                border-bottom: none;
            }
            
            .relation-content {
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .relation-entity {
                color: #007bff;
                text-decoration: none;
                
                &:hover {
                    text-decoration: underline;
                }
            }
            
            .relation-type {
                color: #6c757d;
                font-size: 0.875rem;
            }
        }
    }
    
    .entry-list {
        .entry-item {
            padding: 1rem;
            border-bottom: 1px solid #e9ecef;
            
            &:last-child {
                border-bottom: none;
            }
            
            .entry-header {
                margin-bottom: 0.5rem;
                
                h6 {
                    margin: 0;
                    margin-bottom: 0.25rem;
                }
            }
            
            .entry-content {
                color: #495057;
                margin-bottom: 0.5rem;
            }
        }
    }
    
    .entity-search-results {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #ced4da;
        border-radius: 4px;
        max-height: 200px;
        overflow-y: auto;
        z-index: 1000;
        
        .entity-search-item {
            padding: 0.5rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            
            &:hover {
                background-color: #f8f9fa;
            }
            
            small {
                color: #6c757d;
            }
        }
    }
    
    .modal {
        background-color: rgba(0, 0, 0, 0.5);
    }
}
</style>