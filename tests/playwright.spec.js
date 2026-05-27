/** @type {import('@playwright/test').config} */
module.exports = {
  testDir: '.',
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:8765' },
};
