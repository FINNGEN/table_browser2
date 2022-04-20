var webpack = require("webpack");

module.exports = {
  entry: ["./src/index.tsx"],
  output: {
    path: __dirname + "/static",
    filename: "bundle.js",
  },
  resolve: {
    extensions: [".ts", ".tsx", ".js", ".jsx"],
  },
  module: {
    rules: [
      {
        test: /\.(t|j)sx?$/,
        use: { loader: "ts-loader" },
        exclude: /node_modules/,
      },
      { test: /\.css$/, use: ["style-loader", "css-loader"] },
      {
        enforce: "pre",
        test: /\.js$/,
        exclude: /node_modules/,
        loader: "source-map-loader",
      },
    ],
  },
  devtool: "source-map",
};
