/** @type {import('tailwindcss').Config} */
export default {
    content: [
      './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
      './src/components/**/*.{js,ts,jsx,tsx,mdx}',
      './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
      extend: {
        fontFamily: {
          inter: ['Inter', 'sans-serif'],
        },
        colors: {
          ayaBlack: '#0E0E0E',
          ayaBackground: '#F5F7FB',
          primary: '#3B82F6', // blue-500
          secondary: '#10B981', // emerald-500
        },
      },
    },
    plugins: [],
  };