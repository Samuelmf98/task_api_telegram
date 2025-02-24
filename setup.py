from setuptools import setup, find_packages

setup(
    name='botbasis',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'psycopg2',
        'openai',
        'python-telegram-bot'
    ],
    author='Samuel Marcos Fernadez',
    author_email='samuel.mf1998@.com',
    description='Una biblioteca para interactuar con un chatbot de OpenAI usando un Chat de Telegram como Front.'
)