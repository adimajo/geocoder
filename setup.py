"""
A setuptools based setup module to install geocoder as a package.
"""
import codecs
import os
import re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def long_description():
    with open(os.path.join(here, 'README.md')) as f:
        description = f.read()
    return description


def find_version(file_path, file_name: str = "__init__.py"):
    """
    Get the version from __init__.py file

    Parameters
    ----------
    file_path: path of this file
    file_name: which python file to search for the version

    Returns
    -------
    version
    """
    with codecs.open(os.path.join(file_path, file_name), 'r') as fp:
        version_file = fp.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


if __name__ == "__main__":
    setup(
        setup_requires=["wheel"],
        name='geocoder',
        version=find_version(os.path.join(here, "geocoder")),
        description='geocoder is a (reverse) address to geolocation mapping tool for France',
        long_description=long_description(),
        long_description_content_type="text/markdown",
        url='https://github.com/adimajo/geocoder',
        author='Paulo Emilio de Vilhena, Adrien Ehrhardt',
        author_email='pevilhena2@gmail.com, adrien.ehrhardt@credit-agricole-sa.fr',
        license='Apache Software License',
        classifiers=[
            "Development Status :: 4 - Beta",
            'Intended Audience :: Financial and Insurance Industry',
            'Topic :: Utilities',
            'License :: OSI Approved :: Apache Software License',
            "Programming Language :: Python :: 3 :: Only",
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
        ],
        keywords='Geocoder France',
        packages=find_packages(),
        package_data={
            'geocoder': ['**/*.css', '**/*.ico', '**/*.html']
        },
        install_requires=[],
        test_suite="pytest-runner",
        tests_require=["pytest", "coverage"],
        entry_points={
            'console_scripts': [
                'geocoder = geocoder.geocoding.__main__:main'
            ]
        },
    )
