-*- mode: m4 -*-
AC_PREREQ(2.59c)

dnl If not 1, append datestamp to the version number
m4_define(telepathy_python_released, 0)
dnl The telepathy-python version number (must actually be numeric at the moment)
m4_define(telepathy_python_major_version, 0)
m4_define(telepathy_python_minor_version, 15)
m4_define(telepathy_python_micro_version, 17)

m4_define(telepathy_python_maybe_datestamp,
          m4_esyscmd([if test x]telepathy_python_released[ != x1; then date +.%Y%m%d | tr -d '\n\r'; fi]))

m4_define(telepathy_python_version, telepathy_python_major_version.telepathy_python_minor_version.telepathy_python_micro_version[]telepathy_python_maybe_datestamp)

AC_INIT(telepathy-python, telepathy_python_version,
        [http://bugs.freedesktop.org/enter_bug.cgi?product=Telepathy&component=tp-python])
AM_INIT_AUTOMAKE

m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES])

AC_DEFINE(TELEPATHY_PYTHON_MAJOR_VERSION, telepathy_python_major_version, [telepathy-python major version])
AC_SUBST(TELEPATHY_PYTHON_MAJOR_VERSION, telepathy_python_major_version)
AC_DEFINE(TELEPATHY_PYTHON_MINOR_VERSION, telepathy_python_minor_version, [telepathy-python minor version])
AC_SUBST(TELEPATHY_PYTHON_MINOR_VERSION, telepathy_python_minor_version)
AC_DEFINE(TELEPATHY_PYTHON_MICRO_VERSION, telepathy_python_micro_version, [telepathy-python micro version])
AC_SUBST(TELEPATHY_PYTHON_MICRO_VERSION, telepathy_python_micro_version)
AC_DEFINE(TELEPATHY_PYTHON_RELEASED, telepathy_python_released, [telepathy-python released])
AC_SUBST(TELEPATHY_PYTHON_RELEASED, telepathy_python_released)

AM_PATH_PYTHON(2.4.0)

XSLTPROC=
AC_CHECK_PROGS([XSLTPROC], [xsltproc])
if test -z "$XSLTPROC"; then
  AC_MSG_ERROR([xsltproc (from the libxslt source package) is required])
fi

AC_CONFIG_FILES(
  Makefile
  examples/Makefile
  src/Makefile
  spec/Makefile
  src/client/Makefile
  src/server/Makefile
  tools/Makefile
  src/_version.py)
AC_OUTPUT
