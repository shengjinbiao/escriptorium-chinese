<template>
    <div class="escr-ai-panel">
        <p class="escr-ai-panel__help">
            Use AI tools to add punctuation or modern Chinese translation to {{ scopeLabel }}.
        </p>
        <ul class="escr-ai-panel__actions">
            <li>
                <EscrButton
                    color="text"
                    :disabled="isDisabled"
                    :on-click="() => trigger({ punctuate: true, translate: false })"
                    label="Generate Punctuation"
                />
            </li>
            <li>
                <EscrButton
                    color="text"
                    :disabled="isDisabled"
                    :on-click="() => trigger({ punctuate: false, translate: true })"
                    label="Generate Translation"
                />
            </li>
            <li>
                <EscrButton
                    color="text"
                    :disabled="isDisabled"
                    :on-click="() => trigger({ punctuate: true, translate: true })"
                    label="Punctuation & Translation"
                />
            </li>
        </ul>
    </div>
</template>

<script>
import EscrButton from "../Button/Button.vue";
import "./AiActionsPanel.css";

export default {
    name: "AiActionsPanel",
    components: {
        EscrButton,
    },
    props: {
        data: {
            type: Object,
            required: true,
        },
    },
    computed: {
        isDisabled() {
            return Boolean(this.data?.disabled) || Boolean(this.data?.processing);
        },
        scopeLabel() {
            return this.data?.scopeLabel || "the current selection";
        },
    },
    methods: {
        trigger(operations) {
            if (this.isDisabled) return;
            const handler = this.data?.onRun;
            if (typeof handler === "function") {
                handler(operations);
            }
        },
    },
};
</script>
