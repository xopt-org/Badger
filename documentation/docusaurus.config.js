// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

const lightCodeTheme = require('prism-react-renderer').themes.github
const darkCodeTheme = require('prism-react-renderer').themes.dracula

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Badger',
  tagline: 'The Go-To Optimizer in ACR',
  url: 'https://xopt-org.github.io',
  baseUrl: '/Badger/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.ico',
  organizationName: 'xopt-org', // Usually your GitHub org/user name.
  projectName: 'Badger', // Usually your repo name.
  trailingSlash: false,

  presets: [
    [
      '@docusaurus/preset-classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/SLAC-ML/Badger-Home/edit/master/',
          remarkPlugins: [remarkMath],
          rehypePlugins: [rehypeKatex],
        },
        blog: {
          showReadingTime: true,
          editUrl: 'https://github.com/SLAC-ML/Badger-Home/edit/master/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  stylesheets: [
    {
      href: 'https://cdn.jsdelivr.net/npm/katex@0.13.24/dist/katex.min.css',
      type: 'text/css',
      integrity:
        'sha384-odtC+0UGzzFL/6PNoE8rX/SPcQDXBJ+uRepguP4QkPCm2LBxH3FA3y+fKSiJ+AmM',
      crossorigin: 'anonymous',
    },
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'Badger',
        logo: {
          alt: 'Badger Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'doc',
            docId: 'intro',
            position: 'left',
            label: 'Docs',
          },
          {
            to: '/blog',
            label: 'Blog',
            position: 'left',
          },
          {
            type: 'docsVersionDropdown',
            position: 'right',
            // dropdownActiveClassDisabled: true,
          },
          {
            href: 'https://github.com/xopt-org/Badger',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              {
                label: 'Introduction',
                to: '/docs/intro',
              },
              {
                label: 'Tutorial',
                to: '/docs/getting-started/tutorial_0',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'Stack Overflow',
                href: 'https://stackoverflow.com/questions/tagged/badger-opt',
              },
              {
                label: 'Mailing List',
                href: 'mailto:badger-opt@slac.stanford.edu',
              },
              {
                label: 'Slack',
                href: 'https://join.slack.com/share/enQtNzQ1MzcyNTQ1NjAwNC0zZWVkYWQ1OWUxODViYTdjZmNhODVmNmRhMjkwZTQ3ZmM1MGJjYWIzNGRmMzg5MzA1ZjIwMjIxMjMxYjQ0YTVl',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'Blog',
                to: '/blog',
              },
              {
                label: 'GitHub',
                href: 'https://github.com/xopt-org/Badger',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Machine Learning Initiative, SLAC National Accelerator Laboratory. Built with Docusaurus.`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
        additionalLanguages: ['python'],
      },
      algolia: {
        // The application ID provided by Algolia
        appId: 'WPJQG5P0EZ',
        // Public API key: it is safe to commit it
        apiKey: 'b63157c581646ac999c9ce4c3569e3e3',
        indexName: 'badger_xopt-org',
        // Optional: see doc section below
        contextualSearch: true,
        // Optional: Algolia search parameters
        searchParameters: {},
        // Optional: path for search page that enabled by default (`false` to disable it)
        searchPagePath: 'search',
      },
    }),
}

export default config
