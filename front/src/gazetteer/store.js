import Vue from 'vue';
import Vuex from 'vuex';

Vue.use(Vuex);

export default new Vuex.Store({
    state: {
        gazetteers: [],
        currentGazetteer: null,
        entities: [],
        currentEntity: null,
        categories: [],
        loading: false,
        error: null
    },
    
    mutations: {
        SET_LOADING(state, loading) {
            state.loading = loading;
        },
        SET_ERROR(state, error) {
            state.error = error;
        },
        SET_GAZETTEERS(state, gazetteers) {
            state.gazetteers = gazetteers;
        },
        SET_CURRENT_GAZETTEER(state, gazetteer) {
            state.currentGazetteer = gazetteer;
        },
        SET_ENTITIES(state, entities) {
            state.entities = entities;
        },
        SET_CURRENT_ENTITY(state, entity) {
            state.currentEntity = entity;
        },
        SET_CATEGORIES(state, categories) {
            state.categories = categories;
        }
    },
    
    actions: {
        async fetchGazetteers({ commit }, params = {}) {
            commit('SET_LOADING', true);
            try {
                const response = await fetch('/api/gazetteer/gazetteers/?' + new URLSearchParams(params));
                if (!response.ok) throw new Error('加载方志列表失败');
                const data = await response.json();
                commit('SET_GAZETTEERS', data);
            } catch (error) {
                commit('SET_ERROR', error.message);
            } finally {
                commit('SET_LOADING', false);
            }
        },
        
        async fetchGazetteer({ commit }, id) {
            commit('SET_LOADING', true);
            try {
                const response = await fetch(`/api/gazetteer/gazetteers/${id}/`);
                if (!response.ok) throw new Error('加载方志详情失败');
                const data = await response.json();
                commit('SET_CURRENT_GAZETTEER', data);
            } catch (error) {
                commit('SET_ERROR', error.message);
            } finally {
                commit('SET_LOADING', false);
            }
        },
        
        async fetchEntities({ commit }, params = {}) {
            commit('SET_LOADING', true);
            try {
                const response = await fetch('/api/gazetteer/entities/?' + new URLSearchParams(params));
                if (!response.ok) throw new Error('加载实体列表失败');
                const data = await response.json();
                commit('SET_ENTITIES', data);
            } catch (error) {
                commit('SET_ERROR', error.message);
            } finally {
                commit('SET_LOADING', false);
            }
        },
        
        async fetchEntity({ commit }, id) {
            commit('SET_LOADING', true);
            try {
                const response = await fetch(`/api/gazetteer/entities/${id}/`);
                if (!response.ok) throw new Error('加载实体详情失败');
                const data = await response.json();
                commit('SET_CURRENT_ENTITY', data);
            } catch (error) {
                commit('SET_ERROR', error.message);
            } finally {
                commit('SET_LOADING', false);
            }
        },
        
        async fetchCategories({ commit }) {
            commit('SET_LOADING', true);
            try {
                const response = await fetch('/api/gazetteer/categories/');
                if (!response.ok) throw new Error('加载分类列表失败');
                const data = await response.json();
                commit('SET_CATEGORIES', data);
            } catch (error) {
                commit('SET_ERROR', error.message);
            } finally {
                commit('SET_LOADING', false);
            }
        }
    }
});