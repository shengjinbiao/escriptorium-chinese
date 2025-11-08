module.exports = {
  "stories": [
    "../src/**/*.stories.mdx",
    "../src/**/*.stories.@(js|jsx|ts|tsx)"
  ],

  "addons": [
    "@storybook/addon-links",
    "storybook-addon-themes",
    "@storybook/addon-a11y",
    "storybook-addon-mock",
    "@storybook/addon-docs"
  ],

  "framework": "@storybook/vue",

  "core": {
    "builder": "@storybook/builder-webpack5"
  },

  features: {
    backgrounds: false
  }
}
