# Front end tooling

## What's required

To install node on the host machine we recommend using [`nvm`](https://github.com/creationix/nvm). Once you have `nvm` installed simply run `nvm install` to install and activate the version of node required for the project. Refer to the [`nvm` documentation](https://github.com/creationix/nvm#usage) for more details about available commands.

The tooling is versioned via `package.json`, and the `package-lock.json` lockfile pins all of the project’s direct and transitive dependencies.

### Available npm tasks

#### Linting and Formatting

- `npm run lint` - Runs all linting checks (CSS, JS, and format checks)
- `npm run lint:css` - Checks SASS/CSS files for style issues using stylelint
- `npm run lint:format` - Verifies formatting of all project files using Prettier
- `npm run lint:js` - Runs ESLint to check JavaScript and TypeScript files
- `npm run format` - Automatically formats all project files using Prettier where possible

#### Build Tasks

- `npm run build` - Builds the assets in development mode
- `npm run build:prod` - Builds the assets in production mode with optimizations
- `npm run start` - Starts the development build process with watch mode
- `npm run start:reload` - Runs webpack-dev-server for development with hot reloading on port 3000

#### Accessibility Testing

- `npm run pa11y` - Runs accessibility tests against your local site using pa11y-ci (requires global installation)

## What's included

- [Sass](http://sass-lang.com/) CSS with [auto-prefixing](https://github.com/postcss/autoprefixer).
- [TypeScript](https://www.typescriptlang.org/) for ES2015+ JavaScript, and TypeScript support.
- [webpack-dev-server](https://v4.webpack.js.org/configuration/dev-server/) for autoreloading.
- [Webpack](https://webpack.js.org/) for module bundling.
  - With `ts-loader` to process JavaScript and TypeScript.
  - With `css-loader`, `postcss-loader`, and `sass-loader` to process stylesheets.
- Consideration for images, currently copying the directory only - to avoid slowdowns and non-essential dependencies. We encourage using SVG for UI vectors and pre-optimised UI photograph assets.
- [Build commands](#build-scripts) for generating testable or deployable assets only
- CSS linting with `stylelint`
- JS linting with `eslint`
- [Jest](https://jestjs.io/) for JavaScript unit tests.
- React support
- [Tailwind](https://tailwindcss.com/) A utility-first CSS framework.
- [pa11y-ci](https://github.com/pa11y/pa11y-ci) Accessibility test runner that can be run against multiple URLs

## Developing with it

- To start the development environment, follow instruction in INSTALL.md in the project root
- Source files for developing your project are in `static_src` and the distribution folder for the compiled assets is `static_compiled`. Don't make direct changes to the `static_compiled` directory as they will be overwritten.

## Tests

JavaScript unit tests for this project use [Jest](https://jestjs.io/). Here are commands you can use:

```sh
# Run the whole test suite once.
npm run test
# Run the whole test suite, collecting test coverage information.
npm run test:coverage
# Start Jest in watch mode, to run tests on a subset of the files.
npm run test:watch
```

## Deploying it

### Build scripts

To only build assets for either development or production you can use

- `npm run build` To build development assets
- `npm run build:prod` To build assets with minification and vendor prefixes

## CSS Background images

There is a folder inside `images` called `cssBackgrounds` where you should place any images referenced by the CSS, whether svg, jpg or png. The tooling will detect the image size, and if it is small (less than 1024 bytes), then it will be automatically encoded within the compiled CSS file. Larger images will be synced to the `cssBackgrounds` folder and referenced in the compiled CSS as a separate file.

## Minimising images

We do not include image minimisation as part of the toolchain out the box for these reasons:

1. Developers should always check the quality of images has not been impacted after running the commands

2. The packages involved are large

3. Minimising images on watch would slow the toolchain down considerably

However, you can install the required packages on your local machine and run the minimisation yourself from the command line by following these instructions.

### Minimising svgs

We provide a config file for svgo which has some recommended presets - but always check the file after running the minimising command to check it has not removed any code that you need.

First, install svgo globally if you have not done this previously:

`npm install -g svgo`

You can then run the `svgo` command from the terminal. Here are some examples:

1. Run the command from the root folder of the project, and target all svg files in the `static_src/images` folder, and all subfolders. This will automatically detect the config file and overwrite the files with the new versions:

`svgo -r -f encyctng/encyctng/static_src/images`

2. Run the command from the root folder of the project, and target a specific svg file. Put the output file in another folder for comparison (don't commit this file or folder to git). This will automatically detect the config file.

`svgo encyctng/encyctng/static_src/images/[your-file.svg] -o ./encyctng/encyctng/static_src/optimised_images`

3. Run the command in the same folder as the sprites file and minimise all the svgs in the file (check them all afterwards!). This will automatically detect the config file.

`svgo sprites.html`

If you run the command from outside the project root you may need to pass an explict reference to the config file with the `--config` option.

Full svgo reference: https://www.npmjs.com/package/svgo

## Minimising jpgs and pngs

First, globally install imagemin and imagemin-mozjpeg if you have not done so before. We use the lossy mozjpeg plugin because the default (lossless), imagemin-jpegtran, can result in larger images than the original.

npm install -g imagemin-cli imagemin-mozjpeg imagemin-pngquant

You can then run the `imagemin` command from the terminal. Here are some examples:

1. Run the command from the root folder of the project and minimise all jpegs in the `images` folder. The files will be overwritten by the new version.

`imagemin encyctng/encyctng/static_src/images/\*.{jpg,jpeg} --plugin=mozjpeg --out-dir=./encyctng/encyctng/static_src/images`

2. Run the command from the root folder of the project and target a specific jpeg file. Output the file into another folder for comparison (don't commit this file or folder to git).

`imagemin encyctng/encyctng/static_src/images/[your-file.jpg] --plugin=mozjpeg --out-dir=./encyctng/encyctng/static_src/optimised_images`

3. Run the command on a particular png file and output to a new version of the file. Uses the lossy pngquant plugin instead of the default lossless plugin for better file size reduction.

`imagemin your-file.png --plugin=pngquant > your-file-optimised.png`

Full imagemin-cli reference: https://github.com/imagemin/imagemin-cli
Useful summary table of the plugins: https://web.dev/use-imagemin-to-compress-images/#plugins

## Further details of the packages included

- **autoprefixer** - adds vendor prefixes as necessary for the browsers defined in `browserslist` in the npm config https://www.npmjs.com/package/autoprefixer
- **typescript** - TypeScript compiler, defines which version of the language we use.
- **ts-jest** - TypeScript support for Jest
- **ts-loader** - use TypeScript with webpack - https://www.npmjs.com/package/ts-loader
- **copy-webpack-plugin** - Used to sync images from static_src to static_compiled
- **css-loader** – add support for Webpack to load stylesheets.
- **cssnano** – minify CSS with safe optimisations - https://cssnano.co/.
- **eslint** - lint your javascript https://www.npmjs.com/package/eslint
- **eslint-config-torchbox** - Our custom rules for linting javascript
- **file-loader** - Use to sync background images (larger than 1024 bytes) and fonts to the static_compiled directory, but only those that are actually used
- **jest** - testing framework for JavaScript https://jestjs.io/
- **jest-environment-jsdom** - JSDOM test environment to simulate a DOM environment as if you were in the browser - https://jestjs.io/docs/configuration#testenvironment-string
- **"mini-css-extract-plugin"** - extract CSS generated by Webpack into separate files.
- **postcss** - tool for transforming styles with JS plugins - https://postcss.org/
- **"postcss-loader"** - integrate PostCSS preprocessing into Webpack's styles loading.
- **postcss-custom-properties** - polyfill for CSS custom properties - https://www.npmjs.com/package/postcss-custom-properties
- **stylelint** - Linting for styles - https://stylelint.io
- **stylelint-config-torchbox** - Our custom rules for linting styles
- **sass-loader** - integrate Sass preprocessing into Webpack's styles loading.
- **url-loader** - Used to inline background images that are smaller than 1024 bytes into the CSS
- **webpack** - Bundler for js files (can do much more too) - https://www.npmjs.com/package/webpack https://webpack.js.org/concepts/
- **webpack-cli** - The webpack command calls this behind the scenese (as of webpack v 4) https://www.npmjs.com/package/webpack-cli
- **pa11y-ci** - To keep our build lightweight we haven't added pa11y-ci as a dependency. We recommend installing it globally with `npm install -g pa11y-ci`. This is set up to use your sitemap.xml. When testing, ensure your server is running at localhost:8000 and your sitemap exists.
