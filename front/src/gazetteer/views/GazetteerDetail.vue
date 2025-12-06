<template>
    <div class="gazetteer-detail" v-if="gazetteer">
        <div class="gazetteer-detail__header">
            <h2>{{ gazetteer.title }}</h2>
            <div class="gazetteer-meta">
                <span class="badge badge-secondary mr-2">
                    {{ gazetteer.dynasty_name }}
                </span>
                <span class="badge badge-info mr-2" v-if="gazetteer.year">
                    {{ gazetteer.year }}年
                </span>
                <span class="badge badge-primary" v-if="gazetteer.location_name">
                    {{ gazetteer.location_name }}
                </span>
            </div>
        </div>

        <div class="gazetteer-detail__content">
            <div class="row">
                <!-- 左侧信息 -->
                <div class="col-md-4">
                    <div class="card mb-4">
                        <div class="card-body">
                            <h5 class="card-title">基本信息</h5>
                            <table class="table table-sm">
                                <tbody>
                                    <tr>
                                        <th>修志人</th>
                                        <td>{{ gazetteer.compiler || '未知' }}</td>
                                    </tr>
                                    <tr>
                                        <th>朝代</th>
                                        <td>{{ gazetteer.dynasty_name }}</td>
                                    </tr>
                                    <tr>
                                        <th>年份</th>
                                        <td>{{ gazetteer.year || '未知' }}</td>
                                    </tr>
                                    <tr>
                                        <th>地点</th>
                                        <td>{{ gazetteer.location_name }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class="card mb-4">
                        <div class="card-body">
                            <h5 class="card-title">描述</h5>
                            <p class="card-text">{{ gazetteer.description || '暂无描述' }}</p>
                        </div>
                    </div>
                </div>

                <!-- 右侧内容 -->
                <div class="col-md-8">
                    <!-- 条目分类列表 -->
                    <div class="card mb-4">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="card-title mb-0">知识条目</h5>
                                <button class="btn btn-sm btn-primary" @click="showAddEntryDialog">
                                    添加条目
                                </button>
                            </div>

                            <div class="category-tabs">
                                <ul class="nav nav-tabs">
                                    <li class="nav-item">
                                        <a class="nav-link"
                                           :class="{ active: selectedCategory === null }"
                                           @click="selectedCategory = null">
                                            全部
                                        </a>
                                    </li>
                                    <li class="nav-item" v-for="category in categories" :key="category.id">
                                        <a class="nav-link"
                                           :class="{ active: selectedCategory === category.id }"
                                           @click="selectedCategory = category.id">
                                            {{ category.name }}
                                        </a>
                                    </li>
                                </ul>
                            </div>

                            <div class="entry-list mt-3">
                                <div v-if="loading" class="text-center py-4">
                                    <div class="spinner-border" role="status">
                                        <span class="sr-only">加载中...</span>
                                    </div>
                                </div>

                                <div v-else-if="filteredEntries.length === 0" class="text-center py-4">
                                    暂无条目
                                </div>

                                <div v-else class="list-group">
                                    <div v-for="entry in filteredEntries"
                                         :key="entry.id"
                                         class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-start">
                                            <div>
                                                <h6 class="mb-1">{{ entry.title }}</h6>
                                                <p class="mb-1 text-muted">
                                                    <small>
                                                        {{ entry.category_name }}
                                                        <span v-if="entry.source_page">
                                                            · 第{{ entry.source_page }}页
                                                        </span>
                                                    </small>
                                                </p>
                                                <p class="mb-0">{{ truncate(entry.content) }}</p>
                                            </div>
                                            <div class="ml-3">
                                                <button class="btn btn-sm btn-outline-primary"
                                                        @click="editEntry(entry)">
                                                    编辑
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 相关实体 -->
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="card-title mb-0">相关实体</h5>
                                <router-link 
                                    :to="{ name: 'entity-list', query: { gazetteer: gazetteer.id }}"
                                    class="btn btn-sm btn-outline-primary">
                                    查看全部
                                </router-link>
                            </div>

                            <div class="entity-list">
                                <div v-if="!entities.length" class="text-center py-4">
                                    暂无相关实体
                                </div>

                                <div v-else class="row">
                                    <div v-for="entity in entities.slice(0, 6)"
                                         :key="entity.id"
                                         class="col-md-4 mb-3">
                                        <div class="card">
                                            <div class="card-body">
                                                <h6 class="card-title">{{ entity.name }}</h6>
                                                <p class="card-text">
                                                    <small class="text-muted">
                                                        {{ entity.type }}
                                                    </small>
                                                </p>
                                                <router-link
                                                    :to="{ name: 'entity-detail', params: { id: entity.id }}"
                                                    class="btn btn-sm btn-link">
                                                    详情
                                                </router-link>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 添加/编辑条目对话框 -->
        <div v-if="showEntryDialog" class="modal fade show" style="display: block;">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            {{ editingEntry ? '编辑条目' : '添加条目' }}
                        </h5>
                        <button type="button" class="close" @click="closeEntryDialog">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <form @submit.prevent="saveEntry">
                            <div class="form-group">
                                <label>标题</label>
                                <input type="text"
                                       v-model="entryForm.title"
                                       class="form-control"
                                       required>
                            </div>
                            <div class="form-group">
                                <label>分类</label>
                                <select v-model="entryForm.category"
                                        class="form-control"
                                        required>
                                    <option value="">请选择分类</option>
                                    <option v-for="category in categories"
                                            :key="category.id"
                                            :value="category.id">
                                        {{ category.name }}
                                    </option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>内容</label>
                                <textarea v-model="entryForm.content"
                                          class="form-control"
                                          rows="5"
                                          required></textarea>
                            </div>
                            <div class="form-group">
                                <label>原书页码</label>
                                <input type="number"
                                       v-model="entryForm.source_page"
                                       class="form-control">
                            </div>
                            <div class="text-right">
                                <button type="button"
                                        class="btn btn-secondary mr-2"
                                        @click="closeEntryDialog">
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
    name: 'GazetteerDetail',
    
    props: {
        id: {
            type: [Number, String],
            required: true
        }
    },
    
    data() {
        return {
            selectedCategory: null,
            showEntryDialog: false,
            editingEntry: null,
            entryForm: this.getEmptyEntryForm(),
            categories: [],  // 从API获取
            entities: []     // 从API获取
        };
    },
    
    computed: {
        ...mapState({
            gazetteer: state => state.currentGazetteer,
            loading: state => state.loading,
            error: state => state.error
        }),
        
        filteredEntries() {
            if (!this.gazetteer?.entries) return [];
            return this.selectedCategory
                ? this.gazetteer.entries.filter(e => e.category === this.selectedCategory)
                : this.gazetteer.entries;
        }
    },
    
    methods: {
        ...mapActions(['fetchGazetteer']),
        
        getEmptyEntryForm() {
            return {
                title: '',
                category: '',
                content: '',
                source_page: null
            };
        },
        
        async loadCategories() {
            try {
                const response = await fetch('/api/gazetteer/categories/');
                if (!response.ok) throw new Error('加载分类失败');
                this.categories = await response.json();
            } catch (error) {
                console.error('加载分类失败:', error);
            }
        },
        
        async loadEntities() {
            try {
                const response = await fetch(`/api/gazetteer/gazetteers/${this.id}/entities/`);
                if (!response.ok) throw new Error('加载实体失败');
                this.entities = await response.json();
            } catch (error) {
                console.error('加载实体失败:', error);
            }
        },
        
        showAddEntryDialog() {
            this.editingEntry = null;
            this.entryForm = this.getEmptyEntryForm();
            this.showEntryDialog = true;
        },
        
        editEntry(entry) {
            this.editingEntry = entry;
            this.entryForm = {
                title: entry.title,
                category: entry.category,
                content: entry.content,
                source_page: entry.source_page
            };
            this.showEntryDialog = true;
        },
        
        closeEntryDialog() {
            this.showEntryDialog = false;
            this.editingEntry = null;
            this.entryForm = this.getEmptyEntryForm();
        },
        
        async saveEntry() {
            try {
                const url = this.editingEntry
                    ? `/api/gazetteer/entries/${this.editingEntry.id}/`
                    : '/api/gazetteer/entries/';
                    
                const response = await fetch(url, {
                    method: this.editingEntry ? 'PUT' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        ...this.entryForm,
                        gazetteer: this.id
                    })
                });
                
                if (!response.ok) throw new Error('保存失败');
                
                // 重新加载方志数据
                await this.fetchGazetteer(this.id);
                this.closeEntryDialog();
                
            } catch (error) {
                console.error('保存条目失败:', error);
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
    
    async created() {
        await Promise.all([
            this.fetchGazetteer(this.id),
            this.loadCategories(),
            this.loadEntities()
        ]);
    }
};
</script>

<style lang="scss" scoped>
.gazetteer-detail {
    padding: 2rem;
    
    &__header {
        margin-bottom: 2rem;
        
        h2 {
            margin-bottom: 1rem;
        }
        
        .gazetteer-meta {
            .badge {
                font-size: 0.9rem;
            }
        }
    }
    
    .card {
        margin-bottom: 1rem;
        
        &:last-child {
            margin-bottom: 0;
        }
    }
    
    .nav-tabs {
        .nav-link {
            cursor: pointer;
        }
    }
    
    .list-group-item {
        &:hover {
            background-color: #f8f9fa;
        }
    }
    
    .modal {
        background-color: rgba(0, 0, 0, 0.5);
    }
}
</style>