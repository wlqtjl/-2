/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        blue: {
          50: '#E6F1FB',
          600: '#185FA5',
        },
        purple: {
          50: '#EEEDFE',
          600: '#534AB7',
        },
        teal: {
          50: '#E1F5EE',
          600: '#0F6E56',
        },
        amber: {
          50: '#FAEEDA',
          600: '#854F0B',
        },
        coral: {
          50: '#FAECE7',
          600: '#993C1D',
        },
        green: {
          50: '#EAF3DE',
          600: '#3B6D11',
        },
        gray: {
          50: '#F1EFE8',
          400: '#D3D1C7',
          500: '#5F5E5A',
          700: '#5F5E5A',
        },
      },
    },
  },
  plugins: [],
}
