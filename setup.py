from setuptools import setup, find_packages

version = '0.2'

setup(name='pyramidion',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[],
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Stefano Fontanelli',
      author_email='s.fontanelli@asidev.com',
      url='',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=['deformalchemy', 'crudalchemy', 'pyramid'],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
