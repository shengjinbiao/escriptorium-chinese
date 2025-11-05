// Initial state
export const initialState = () => ({
    visibleEntities: [],
    selectedEntity: null,
    entityTypes: [
        { id: 'PER', name: '人名', color: '#f56a00' },
        { id: 'LOC', name: '地名', color: '#7cb305' },
        { id: 'ORG', name: '组织机构', color: '#1890ff' },
        { id: 'TIME', name: '时间', color: '#722ed1' },
        { id: 'DATE', name: '日期', color: '#eb2f96' },
        { id: 'DYNASTY', name: '朝代', color: '#fa8c16' },
        { id: 'EVENT', name: '事件', color: '#13c2c2' },
        { id: 'OTHER', name: '其他', color: '#8c8c8c' }
    ],
    pendingChanges: new Set(),
    lastError: null
});

// Mutations
export const mutations = {
    setVisibleEntities(state, entities) {
        state.visibleEntities = entities;
    },

    setSelectedEntity(state, entity) {
        state.selectedEntity = entity;
    },

    addPendingChange(state, entityId) {
        state.pendingChanges.add(entityId);
    },

    removePendingChange(state, entityId) {
        state.pendingChanges.delete(entityId);
    },

    setError(state, error) {
        state.lastError = error;
    }
};

// Actions
export const actions = {
    async setVisibleEntities({ commit }, entities) {
        commit('setVisibleEntities', entities);
    },

    async updateEntityInspector({ commit, state }, entity) {
        if (!entity) {
            commit('setSelectedEntity', null);
            return;
        }

        // 合并实体属性与类型信息
        const entityType = state.entityTypes.find(type => type.id === entity.type);
        if (entityType) {
            entity = {
                ...entity,
                typeInfo: entityType
            };
        }

        commit('setSelectedEntity', entity);
    },

    async updateEntity({ commit, dispatch }, { entity, changes }) {
        try {
            commit('addPendingChange', entity.id);
            
            // TODO: 调用后端API更新实体
            
            commit('removePendingChange', entity.id);
            await dispatch('updateEntityInspector', {
                ...entity,
                ...changes
            });
        } catch (error) {
            commit('setError', error);
            throw error;
        }
    }
};

// Getters
export const getters = {
    getEntityById: state => id => {
        return state.visibleEntities.find(e => e.id === id);
    },
    
    isPending: state => id => {
        return state.pendingChanges.has(id);
    },

    getEntityTypeById: state => id => {
        return state.entityTypes.find(type => type.id === id);
    }
};

export default {
    namespaced: true,
    state: initialState(),
    mutations,
    actions,
    getters
};