export const state = () => ({
    viewport: {
        scrollTop: 0,
        scrollLeft: 0,
        width: 0,
        height: 0
    }
});

export const mutations = {
    setViewport(state, { scrollTop, scrollLeft, width, height }) {
        state.viewport = {
            scrollTop,
            scrollLeft,
            width: width || state.viewport.width,
            height: height || state.viewport.height
        };
    }
};

export const actions = {
    updateViewport({ commit }, viewport) {
        commit('setViewport', viewport);
    }
};

export default {
    namespaced: true,
    state,
    mutations,
    actions
};