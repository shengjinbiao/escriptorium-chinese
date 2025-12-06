<template>
    <aside class="knowledge-panel">
        <header class="knowledge-panel__header">
            <h4>知识库</h4>
            <div class="knowledge-panel__toolbar">
                <button 
                    class="btn btn-sm btn-outline-primary" 
                    @click="createEntity"
                    :disabled="disabled">
                    <i class="fas fa-plus"></i>
                    添加实体
                </button>
            </div>
        </header>
        
        <div class="knowledge-panel__content">
            <!-- 搜索框 -->
            <div class="search-box">
                <input 
                    type="text" 
                    v-model="searchQuery"
                    class="form-control form-control-sm"
                    placeholder="搜索实体..."
                >
            </div>
            
            <!-- 实体分类列表 -->
            <div class="entity-categories">
                <div 
                    v-for="category in categories" 
                    :key="category.id"
                    class="entity-category"
                >
                    <div 
                        class="entity-category__header"
                        @click="toggleCategory(category.id)"
                    >
                        <i 
                            class="fas" 
                            :class="expandedCategories.includes(category.id) ? 'fa-chevron-down' : 'fa-chevron-right'"
                        ></i>
                        <span>{{ category.name }}</span>
                        <span class="badge badge-info">{{ category.entities.length }}</span>
                    </div>
                    
                    <transition name="slide">
                        <div 
                            v-if="expandedCategories.includes(category.id)"
                            class="entity-category__content"
                        >
                            <div 
                                v-for="entity in filteredEntities(category.entities)" 
                                :key="entity.id"
                                class="entity-item"
                                :class="{ 'entity-item--selected': selectedEntity && selectedEntity.id === entity.id }"
                                @click="selectEntity(entity)"
                            >
                                <span class="entity-item__text">{{ entity.text }}</span>
                                <small class="entity-item__type">{{ entity.type }}</small>
                            </div>
                        </div>
                    </transition>
                </div>
            </div>
        </div>
        
        <!-- 实体详情弹窗 -->
        <div v-if="showEntityDialog" class="entity-dialog">
            <div class="entity-dialog__content">
                <h5>{{ isEditing ? '编辑实体' : '添加新实体' }}</h5>
                <form @submit.prevent="saveEntity">
                    <div class="form-group">
                        <label>名称</label>
                        <input 
                            v-model="entityForm.text" 
                            type="text" 
                            class="form-control"
                            required
                        >
                    </div>
                    <div class="form-group">
                        <label>类型</label>
                        <select v-model="entityForm.type" class="form-control" required>
                            <option value="">请选择类型</option>
                            <option 
                                v-for="type in entityTypes" 
                                :key="type.id" 
                                :value="type.id"
                            >
                                {{ type.name }}
                            </option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>描述</label>
                        <textarea 
                            v-model="entityForm.description" 
                            class="form-control"
                            rows="3"
                        ></textarea>
                    </div>
                    <div class="entity-dialog__actions">
                        <button type="button" class="btn btn-secondary" @click="closeDialog">取消</button>
                        <button type="submit" class="btn btn-primary">保存</button>
                    </div>
                </form>
            </div>
        </div>
    </aside>
</template>

<script>
export default {
    name: 'KnowledgePanel',
    
    props: {
        disabled: {
            type: Boolean,
            default: false
        }
    },
    
    data() {
        return {
            searchQuery: '',
            expandedCategories: [],
            categories: [],
            selectedEntity: null,
            showEntityDialog: false,
            isEditing: false,
            entityForm: {
                text: '',
                type: '',
                description: ''
            }
        };
    },
    
    computed: {
        entityTypes() {
            // 从store获取实体类型列表
            return this.$store.state.entityTypes || [];
        }
    },
    
    methods: {
        toggleCategory(categoryId) {
            const index = this.expandedCategories.indexOf(categoryId);
            if (index === -1) {
                this.expandedCategories.push(categoryId);
            } else {
                this.expandedCategories.splice(index, 1);
            }
        },
        
        filteredEntities(entities) {
            if (!this.searchQuery) return entities;
            
            const query = this.searchQuery.toLowerCase();
            return entities.filter(entity => 
                entity.text.toLowerCase().includes(query) ||
                entity.type.toLowerCase().includes(query)
            );
        },
        
        selectEntity(entity) {
            this.selectedEntity = entity;
            this.$emit('select', entity);
        },
        
        createEntity() {
            this.isEditing = false;
            this.entityForm = {
                text: '',
                type: '',
                description: ''
            };
            this.showEntityDialog = true;
        },
        
        editEntity(entity) {
            this.isEditing = true;
            this.entityForm = { ...entity };
            this.showEntityDialog = true;
        },
        
        closeDialog() {
            this.showEntityDialog = false;
        },
        
        async saveEntity() {
            try {
                const response = await fetch('/api/knowledge/entities/', {
                    method: this.isEditing ? 'PUT' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify(this.entityForm)
                });
                
                if (!response.ok) {
                    throw new Error('保存失败');
                }
                
                const result = await response.json();
                
                this.$store.dispatch('alerts/add', {
                    message: `实体${this.isEditing ? '更新' : '创建'}成功`,
                    type: 'success'
                });
                
                this.closeDialog();
                await this.loadEntities();
            } catch (error) {
                this.$store.dispatch('alerts/addError', {
                    message: error.message
                });
            }
        },
        
        async loadEntities() {
            try {
                const response = await fetch('/api/knowledge/entities/');
                if (!response.ok) throw new Error('加载失败');
                
                const data = await response.json();
                // 按类型分组
                this.categories = Object.entries(
                    data.reduce((acc, entity) => {
                        if (!acc[entity.type]) acc[entity.type] = [];
                        acc[entity.type].push(entity);
                        return acc;
                    }, {})
                ).map(([type, entities]) => ({
                    id: type,
                    name: type,
                    entities
                }));
            } catch (error) {
                this.$store.dispatch('alerts/addError', {
                    message: '加载实体列表失败: ' + error.message
                });
            }
        }
    },
    
    created() {
        this.loadEntities();
    }
};
</script>

<style lang="scss" scoped>
.knowledge-panel {
    display: flex;
    flex-direction: column;
    border-left: 1px solid #e5e7eb;
    background-color: white;
    height: 100%;

    &__header {
        padding: 1rem;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        justify-content: space-between;
        align-items: center;

        h4 {
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
        }
    }

    &__content {
        flex: 1;
        overflow-y: auto;
        padding: 1rem;
    }
}

.search-box {
    margin-bottom: 1rem;
}

.entity-category {
    margin-bottom: 0.5rem;
    
    &__header {
        display: flex;
        align-items: center;
        padding: 0.5rem;
        background-color: #f9fafb;
        cursor: pointer;
        user-select: none;
        border-radius: 4px;
        
        &:hover {
            background-color: #f3f4f6;
        }
        
        i {
            margin-right: 0.5rem;
            width: 1rem;
        }
        
        .badge {
            margin-left: auto;
        }
    }
    
    &__content {
        padding: 0.5rem 0 0.5rem 1.5rem;
    }
}

.entity-item {
    display: flex;
    align-items: center;
    padding: 0.5rem;
    cursor: pointer;
    border-radius: 4px;
    
    &:hover {
        background-color: #f9fafb;
    }
    
    &--selected {
        background-color: #e5e7eb;
    }
    
    &__text {
        flex: 1;
    }
    
    &__type {
        color: #6b7280;
    }
}

.entity-dialog {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    
    &__content {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
        width: 90%;
        max-width: 500px;
    }
    
    &__actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-top: 1rem;
    }
}

.slide-enter-active,
.slide-leave-active {
    transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
    opacity: 0;
    transform: translateY(-10px);
}
</style>
