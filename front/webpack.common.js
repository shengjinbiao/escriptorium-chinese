const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const VueLoaderPlugin = require("vue-loader/lib/plugin");
const CompressionPlugin = require("compression-webpack-plugin");

module.exports = {
    entry: {
        vendor: "./src/vendor.js",
        main: "./src/main.js",
        editor: "./src/editor/main.js",
        doclist: "./src/documentlist/main.js",
        docstasks: "./src/documentstasks/main.js",
        documentDashboard: "./vue/exports/documentDashboard.js",
        globalNavigation: "./vue/exports/globalNavigation.js",
        projectDashboard: "./vue/exports/projectDashboard.js",
        projectsList: "./vue/exports/projectsList.js",
        imagesPage: "./vue/exports/imagesPage.js",
        gazetteer: "./src/gazetteer/main.js",
    },

    output: {
        filename: "[name].js",
        path: path.resolve(__dirname, "./dist/"),
        publicPath: "",
    },

    plugins: [
        new MiniCssExtractPlugin(),
        new VueLoaderPlugin(),
        new CompressionPlugin({
            test: /\.(js|css)$/,
        }),
    ],

    module: {
        rules: [
            {
                test: /\.(css|scss)$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    {
                        loader: "css-loader",
                        options: {
                            url: true,
                        },
                    },
                    {
                        loader: "resolve-url-loader"},
                    {
                        loader: "sass-loader",
                        options: {
                            sourceMap: true,
                        },
                    },
                ],
            },
            {
                test: /\.(png|jpe?g|gif|woff|woff2|eot|ttf|otf|svg)$/i,
                use: ["file-loader"],
            },
            {
                test: /\.vue$/,
                use: [{ loader: "vue-loader", options: { prettify: false } }],
            },
        ],
    },

    resolve: {
        alias: {
            vue$: "vue/dist/vue",
        },
    },
};
