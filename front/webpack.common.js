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
                    {
                        loader: MiniCssExtractPlugin.loader,
                        options: { publicPath: "/static/" },
                    },
                    {
                        loader: "css-loader",
                        options: {
                            url: {
                                filter: (url) => !url.startsWith("/static/webfonts/"),
                            },
                        },
                    },
                    "sass-loader"
                ],
            },
            {
                test: /\.(woff2?|eot|ttf|otf|svg)$/i,
                type: "asset/resource",
                generator: {
                    filename: "webfonts/[name][ext]",
                    publicPath: "/static/",
                },
            },
            {
                test: /\.(png|jpe?g|gif)$/i,
                type: "asset/resource",
                generator: {
                    filename: "images/[name][ext]",
                    publicPath: "/static/",
                },
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
