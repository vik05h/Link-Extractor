import pkg from '../package.json';

/** The app version, from package.json. scripts/set_version.py keeps it in step with the Python side. */
export const APP_VERSION = `v${pkg.version}`;

/** localStorage key that shows What's New once for each version. */
export const FIRST_RUN_KEY = `le_first_run_${APP_VERSION}`;
