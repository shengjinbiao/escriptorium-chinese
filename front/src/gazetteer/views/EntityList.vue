<template>
    <div class="entity-list">
        <div class="entity-list__header">
            <h2>知识实体</h2>
            <div class="entity-list__filters">
                <!-- 搜索和筛选 -->
                <div class="form-group">
                    <label>实体类型</label>
                    <select v-model="filters.type" class="form-control">
                        <option value="">全部类型</option>
                        <option v-for="type in entityTypes"
                                :key="type.value"
                                :value="type.value">
                            {{ type.label }}
                        </option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>搜索</label>
                    <input type="text"
                           v-model="filters.search"
                           class="form-control"
                           placeholder="输入实体名称">
                </div>
                
                <button class="btn btn-primary" @click="search">
                    搜索
                </button>
                
                <button class="btn btn-outline-primary ml-auto"
                        @click="showAddEntityDialog">
                    添加实体
                </button>
            </div>
        </div>

        <div class="entity-list__content">
            <div v-if="loading" class="text-center py-4">
                <div class="spinner-border" role="status">
                    <span class="sr-only">加载中...</span>
                </div>
            </div>

            <div v-else-if="error" class="alert alert-danger">
                {{ error }}
            </div>

            <div v-else>
                <!-- 网格视图 -->
                <div class="row">
                    <div v-for="entity in entities"
                         :key="entity.id"
                         class="col-md-4 col-lg-3 mb-4">
                        <div class="card h-100">
                            <div class="card-body">
                                <h5 class="card-title">{{ entity.name }}</h5>
                                <p class="card-text">
                                    <span class="badge"
                                          :class="getTypeClass(entity.type)">
                                        {{ getTypeLabel(entity.type) }}
                                    </span>
                                </p>
                                <p class="card-text">
                                    {{ truncate(entity.description) }}
                                </p>
                                <div class="card-text small text-muted mb-3">
                                    相关条目: {{ entity.entries.length }}
                                </div>
                                <router-link
                                    :to="{ name: 'entity-detail', params: { id: entity.id }}"
                                    class="btn btn-sm btn-outline-primary">
                                    查看详情
                                </router-link>
                            </div>
                        </div>
                    </div>
                </div>

                <div v-if="!entities.length" class="text-center py-4">
                    暂无数据
                </div>
            </div>
        </div>

        <!-- 添加/编辑实体对话框 -->
        <div v-if="showEntityDialog" class="modal fade show" style="display: block;">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            {{ editingEntity ? '编辑实体' : '添加实体' }}
                        </h5>
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
                                    <option value="">请选择类型</option>
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
    </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';

export default {
    name: 'EntityList',
    
    data() {
        return {
            filters: {
                type: '',
                search: ''
            },
            showEntityDialog: false,
            editingEntity: null,
            entityForm: this.getEmptyEntityForm(),
            entityTypes: [
                { value: 'person', label: '人物' },
                { value: 'place', label: '地点' },
                { value: 'event', label: '事件' },
                { value: 'org', label: '机构' },
                { value: 'other', label: '其他' }
            ]
        };
    },
    
    computed: {
        ...mapState({
            entities: state => state.entities,
            loading: state => state.loading,
            error: state => state.error
        })
    },
    
    methods: {
        ...mapActions(['fetchEntities']),
        
        getEmptyEntityForm() {
            return {
                name: '',
                type: '',
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
        
        async search() {
            const params = Object.entries(this.filters)
                .filter(([_, value]) => value !== '')
                .reduce((acc, [key, value]) => ({...acc, [key]: value}), {});
                
            if (this.$route.query.gazetteer) {
                params.gazetteer = this.$route.query.gazetteer;
            }
            
            await this.fetchEntities(params);
        },
        
        showAddEntityDialog() {
            this.editingEntity = null;
            this.entityForm = this.getEmptyEntityForm();
            this.showEntityDialog = true;
        },
        
        closeEntityDialog() {
            this.showEntityDialog = false;
            this.editingEntity = null;
            this.entityForm = this.getEmptyEntityForm();
        },
        
        async saveEntity() {
            try {
                const url = this.editingEntity
                    ? `/api/gazetteer/entities/${this.editingEntity.id}/`
                    : '/api/gazetteer/entities/';
                    
                const response = await fetch(url, {
                    method: this.editingEntity ? 'PUT' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify(this.entityForm)
                });
                
                if (!response.ok) throw new Error('保存失败');
                
                await this.search();
                this.closeEntityDialog();
                
            } catch (error) {
                console.error('保存实体失败:', error);
                // TODO: 显示错误提示
            }
        },
        
        truncate(text, length = 100) {
            if (!text) return '';
            return text.length > length
                ? text.slice(0, length) + '...'
                : text;
        }
    },
    
    created() {
        this.search();
    }
};
</script>

<style lang="scss" scoped>
.entity-list {
    padding: 2rem;
    
    &__header {
        margin-bottom: 2rem;
        
        h2 {
            margin-bottom: 1rem;
        }
    }
    
    &__filters {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 4px;
        
        .form-group {
            margin-bottom: 0;
            flex: 1;
        }
    }
    
    .badge {
        padding: 0.5em 0.7em;
        font-size: 0.85em;
    }
    
    .card {
        transition: transform 0.2s;
        
        &:hover {
            transform: translateY(-2px);
        }
    }
    
    .modal {
        background-color: rgba(0, 0, 0, 0.5);
    }
}
</style>