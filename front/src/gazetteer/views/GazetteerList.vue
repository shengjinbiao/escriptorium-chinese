<template>
    <div class="gazetteer-list">
        <div class="gazetteer-list__header">
            <h2>方志列表</h2>
            <div class="gazetteer-list__filters">
                <!-- 筛选条件 -->
                <div class="form-group">
                    <label>朝代</label>
                    <select v-model="filters.dynasty" class="form-control">
                        <option value="">全部</option>
                        <option v-for="dynasty in dynasties"
                                :key="dynasty.id"
                                :value="dynasty.name">
                            {{ dynasty.name }}
                        </option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>地点</label>
                    <input type="text"
                           v-model="filters.location"
                           class="form-control"
                           placeholder="输入地名">
                </div>
                
                <div class="form-group">
                    <label>年份范围</label>
                    <div class="d-flex">
                        <input type="number"
                               v-model.number="filters.year_from"
                               class="form-control"
                               placeholder="起始年">
                        <span class="mx-2">-</span>
                        <input type="number"
                               v-model.number="filters.year_to"
                               class="form-control"
                               placeholder="结束年">
                    </div>
                </div>
                
                <button class="btn btn-primary"
                        @click="search">
                    搜索
                </button>
            </div>
        </div>
        
        <div class="gazetteer-list__content">
            <div v-if="loading" class="text-center py-4">
                <div class="spinner-border" role="status">
                    <span class="sr-only">加载中...</span>
                </div>
            </div>
            
            <div v-else-if="error" class="alert alert-danger">
                {{ error }}
            </div>
            
            <div v-else class="row">
                <div v-for="gazetteer in gazetteers"
                     :key="gazetteer.id"
                     class="col-md-6 col-lg-4 mb-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">{{ gazetteer.title }}</h5>
                            <p class="card-text">
                                <small class="text-muted">
                                    {{ gazetteer.dynasty_name }} · {{ gazetteer.year }}年
                                </small>
                            </p>
                            <p class="card-text">
                                {{ gazetteer.location_name }}
                            </p>
                            <p class="card-text">
                                {{ truncate(gazetteer.description) }}
                            </p>
                            <router-link
                                :to="{ name: 'gazetteer-detail', params: { id: gazetteer.id }}"
                                class="btn btn-outline-primary">
                                查看详情
                            </router-link>
                        </div>
                    </div>
                </div>
            </div>
            
            <div v-if="!loading && !gazetteers.length"
                 class="text-center py-4">
                暂无数据
            </div>
        </div>
    </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';

export default {
    name: 'GazetteerList',
    
    data() {
        return {
            filters: {
                dynasty: '',
                location: '',
                year_from: null,
                year_to: null
            },
            dynasties: []  // 这里应该从API获取朝代列表
        };
    },
    
    computed: {
        ...mapState({
            gazetteers: state => state.gazetteers,
            loading: state => state.loading,
            error: state => state.error
        })
    },
    
    methods: {
        ...mapActions(['fetchGazetteers']),
        
        async search() {
            // 过滤掉空值
            const params = Object.entries(this.filters)
                .filter(([_, value]) => value !== '' && value != null)
                .reduce((acc, [key, value]) => ({...acc, [key]: value}), {});
                
            await this.fetchGazetteers(params);
        },
        
        async loadDynasties() {
            try {
                const response = await fetch('/api/gazetteer/dynasties/');
                if (!response.ok) throw new Error('加载朝代列表失败');
                this.dynasties = await response.json();
            } catch (error) {
                console.error('加载朝代列表失败:', error);
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
        await this.loadDynasties();
        await this.fetchGazetteers();
    }
};
</script>

<style lang="scss" scoped>
.gazetteer-list {
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
        }
    }
    
    .card {
        height: 100%;
        
        &-title {
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }
        
        &-text {
            margin-bottom: 0.5rem;
            
            &:last-child {
                margin-bottom: 0;
            }
        }
    }
}
</style>