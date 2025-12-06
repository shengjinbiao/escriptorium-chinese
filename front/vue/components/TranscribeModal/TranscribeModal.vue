<template>
    <EscrModal
        class="escr-transcribe-modal"
    >
        <template #modal-header>
            <h2>Transcribe {{ scope }}</h2>
            <EscrButton
                color="text"
                :on-click="onCancel"
                size="small"
            >
                <template #button-icon>
                    <XIcon />
                </template>
            </EscrButton>
        </template>
        <template #modal-content>
            <EscrAlert
                color="secondary"
                message="Check accuracy of segmentation prior to transcribing."
            />
            <DropdownField
                label="Model"
                :disabled="disabled || !models"
                :options="modelOptions"
                :on-change="handleModelChange"
                required
            />
            <DropdownField
                v-if="hasExistingLayers"
                label="Existing Layer"
                :disabled="disabled"
                :options="existingLayerOptions"
                :on-change="handleExistingLayerChange"
                help-text="Select an existing transcription layer to append new pages."
            />
            <TextField
                :disabled="disabled || existingLayer"
                :help-text="layerNameHelpText"
                :max-length="512"
                :on-input="handleLayerNameInput"
                :value="layerName"
                placeholder="Enter layer name"
                label="Layer Name"
                required
            />
        </template>
        <template #modal-actions>
            <EscrButton
                color="outline-primary"
                label="Cancel"
                :on-click="onCancel"
                :disabled="disabled"
            />
            <EscrButton
                color="primary"
                label="Transcribe"
                :on-click="onSubmit"
                :disabled="disabled || invalid"
            />
        </template>
    </EscrModal>
</template>
<script>
import { mapActions, mapState } from "vuex";
import DropdownField from "../Dropdown/DropdownField.vue";
import EscrAlert from "../Alert/Alert.vue";
import EscrButton from "../Button/Button.vue";
import EscrModal from "../Modal/Modal.vue";
import TextField from "../TextField/TextField.vue";
import XIcon from "../Icons/XIcon/XIcon.vue";
import "../Common/Form.css";

export default {
    name: "EscrTranscribeModal",
    components: {
        DropdownField,
        EscrAlert,
        EscrButton,
        EscrModal,
        TextField,
        XIcon,
    },
    props: {
        /**
         * Boolean indicating whether or not the form fields should be disabled.
         */
        disabled: {
            type: Boolean,
            required: true,
        },
        /**
         * The list of all OCR models on the document. Should be an array of objects
         * with at least a name and pk for each model.
         */
        models: {
            type: Array,
            required: true,
        },
        /**
         * List of transcription layers on this document.
         */
        transcriptions: {
            type: Array,
            required: true,
        },
        /**
         * Scope of the transcription task, which will appear in the header to indicate
         * whether you are transcribing the entire document or specific images.
         */
        scope: {
            type: String,
            required: true,
        },
        /**
         * Callback function for submitting the transcription task.
         */
        onSubmit: {
            type: Function,
            required: true,
        },
        /**
         * Callback function for clicking "cancel".
         */
        onCancel: {
            type: Function,
            required: true,
        },
    },
    computed: {
        ...mapState({
            model: (state) => state.forms.transcribe.model,
            layerName: (state) => state.forms.transcribe.layerName,
            existingLayer: (state) => state.forms.transcribe.existingLayer,
        }),
        /**
         * this form is invalid and cannot be submitted if it is missing model
         * or layer name
         */
        invalid() {
            if (!this.model) {
                return true;
            }
            if (this.existingLayer) {
                return false;
            }
            return !this.layerName;
        },
        /**
         * convert models to options for select element
         */
        modelOptions() {
            return this.models.map((model) => ({
                label: model.name,
                value: model.pk.toString(),
                selected: this.model.toString() === model.pk.toString(),
            }));
        },
        /**
         * Whether there are any existing transcription layers to show.
         */
        hasExistingLayers() {
            return this.filteredTranscriptions.length > 0;
        },
        /**
         * Convert existing transcription layers to options for select element.
         * Include a leading option for creating a new layer.
         */
        existingLayerOptions() {
            const options = [{
                label: "Create new layer",
                value: "",
                selected: this.existingLayer === "",
            }];
            return options.concat(
                this.filteredTranscriptions.map((transcription) => ({
                    label: transcription.name,
                    value: transcription.pk.toString(),
                    selected: this.existingLayer === transcription.pk.toString(),
                })),
            );
        },
        /**
         * Limit selectable layers to non-archived entries.
         */
        filteredTranscriptions() {
            return this.transcriptions.filter((transcription) => !transcription.archived);
        },
        /**
         * Contextual help text for the layer name input.
         */
        layerNameHelpText() {
            if (this.existingLayer) {
                return "Layer name is locked while using an existing transcription.";
            }
            return "Enter a name for the new transcription layer.";
        },
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
        ]),
        handleLayerNameInput(e) {
            // typing a new layer name clears any existing-layer selection
            if (this.existingLayer) {
                this.handleGenericInput({
                    form: "transcribe", field: "existingLayer", value: "",
                });
            }
            this.handleGenericInput({
                form: "transcribe", field: "layerName", value: e.target.value,
            });
        },
        handleModelChange(e) {
            this.handleGenericInput({ form: "transcribe", field: "model", value: e.target.value });
        },
        handleExistingLayerChange(e) {
            const value = e.target.value;
            this.handleGenericInput({
                form: "transcribe", field: "existingLayer", value,
            });
            if (value) {
                const selection = this.filteredTranscriptions.find(
                    (transcription) => transcription.pk.toString() === value,
                );
                this.handleGenericInput({
                    form: "transcribe",
                    field: "layerName",
                    value: selection ? selection.name : "",
                });
            } else {
                this.handleGenericInput({
                    form: "transcribe",
                    field: "layerName",
                    value: "",
                });
            }
        },
    },
};
</script>
