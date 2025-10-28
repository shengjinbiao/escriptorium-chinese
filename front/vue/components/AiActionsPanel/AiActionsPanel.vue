<template>
    <div class="escr-ai-panel">
        <p class="escr-ai-panel__help">
            Use AI tools to add punctuation, modern Chinese translation, extract entities, or build semantic vectors for {{ scopeLabel }}.
        </p>
        <ul class="escr-ai-panel__actions">
            <template v-if="showTextOperations">
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
            </template>
            <li v-if="allowEntityExtraction">
                <EscrButton
                    color="text"
                    :disabled="isDisabled"
                    :on-click="() => trigger({ punctuate: false, translate: false, entities: true })"
                    label="Extract Entities"
                />
            </li>
            <li v-if="hasVectorize">
                <EscrButton
                    color="text"
                    :disabled="isVectorDisabled"
                    :on-click="triggerVectorize"
                    label="Generate Semantic Vectors"
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
        hasVectorize() {
            return typeof this.data?.onVectorize === "function";
        },
        isVectorizing() {
            return Boolean(this.data?.vectorizing);
        },
        showTextOperations() {
            return this.data?.allowTextOperations !== false;
        },
        allowEntityExtraction() {
            return this.data?.allowEntityExtraction !== false;
        },
        isVectorDisabled() {
            if (!this.hasVectorize) return true;
            return (
                Boolean(this.data?.disabled) ||
                Boolean(this.data?.processing) ||
                this.isVectorizing
            );
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
        triggerVectorize() {
            if (this.isVectorDisabled) return;
            const handler = this.data?.onVectorize;
            if (typeof handler === "function") {
                handler();
            }
        },
    },
};
</script>
