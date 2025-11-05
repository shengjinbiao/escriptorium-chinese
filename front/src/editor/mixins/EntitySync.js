import { debounce } from 'lodash';
import { mapActions, mapState } from 'vuex';

export const EntitySync = {
    computed: {
        ...mapState({
            currentViewport: state => state.editor.viewport,
        }),
    },

    data() {
        return {
            syncDebounceDelay: 300,
            lastSyncTimestamp: 0,
        };
    },

    methods: {
        ...mapActions('entities', [
            'setVisibleEntities',
            'updateEntityInspector'
        ]),

        debouncedSyncEntities: debounce(function() {
            this.syncEntities();
        }, 300),

        async syncEntities() {
            if (!this.anno || !this.$refs.contentContainer) return;

            const now = Date.now();
            if (now - this.lastSyncTimestamp < 100) return;
            this.lastSyncTimestamp = now;

            try {
                // 1. 获取当前可见的实体注释
                const visibleEntities = this.getVisibleEntities();
                
                // 2. 更新Vuex状态
                await this.setVisibleEntities(visibleEntities);
                
                // 3. 如果当前选中的实体在可视区域内，更新inspector
                if (this.selectedEntityId) {
                    const selectedEntity = visibleEntities.find(e => e.id === this.selectedEntityId);
                    if (selectedEntity) {
                        await this.updateEntityInspector(selectedEntity);
                    }
                }

                // 4. 高亮匹配的实体
                this.highlightMatchedEntities(visibleEntities);

            } catch (error) {
                console.error('Entity sync failed:', error);
                this.addError({
                    message: 'Failed to sync entities',
                    error 
                });
            }
        },

        getVisibleEntities() {
            // 获取可视区域的坐标
            const container = this.$refs.contentContainer;
            const { scrollTop, clientHeight } = container;
            const visibleRange = {
                top: scrollTop,
                bottom: scrollTop + clientHeight
            };

            // 过滤出在可视区域内的实体
            return this.entityAnnotations.filter(entity => {
                const element = this.findEntityElement(entity.id);
                if (!element) return false;

                const rect = element.getBoundingClientRect();
                const containerRect = container.getBoundingClientRect();

                // Compute the element position in the scroll container's coordinate space
                const elementTop = rect.top - containerRect.top + scrollTop;
                const elementBottom = elementTop + rect.height;

                return elementBottom >= visibleRange.top && elementTop <= visibleRange.bottom;
            });
        },

        findEntityElement(entityId) {
            return document.querySelector(`[data-entity-id="${entityId}"]`);
        },

        highlightMatchedEntities(visibleEntities) {
            // 移除所有高亮
            document.querySelectorAll('.entity-highlight').forEach(el => {
                el.classList.remove('entity-highlight');
            });

            // 为可见实体添加高亮
            visibleEntities.forEach(entity => {
                const element = this.findEntityElement(entity.id);
                if (element) {
                    element.classList.add('entity-highlight');
                }
            });
        },

        // 监听滚动和调整大小事件
        setupEntitySync() {
            if (!this.$refs.contentContainer) return;

            this.$refs.contentContainer.addEventListener('scroll', this.debouncedSyncEntities);
            window.addEventListener('resize', this.debouncedSyncEntities);

            // 初始同步
            this.syncEntities();
        },

        teardownEntitySync() {
            if (!this.$refs.contentContainer) return;

            this.$refs.contentContainer.removeEventListener('scroll', this.debouncedSyncEntities);
            window.removeEventListener('resize', this.debouncedSyncEntities);
            this.debouncedSyncEntities.cancel();
        }
    },

    mounted() {
        this.setupEntitySync();
    },

    beforeDestroy() {
        this.teardownEntitySync();
    },

    watch: {
        // 当实体数据改变时重新同步
        entityAnnotations: {
            handler() {
                this.debouncedSyncEntities();
            },
            deep: true
        }
    }
};
