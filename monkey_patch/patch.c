#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *
patch_mro(PyObject *self, PyObject *args)
{
    PyTypeObject *dst, *src;

    if (!PyArg_ParseTuple(args, "OO", &dst, &src))
        return NULL;
    Py_INCREF(src->tp_mro);
    Py_DECREF(dst->tp_mro);
    dst->tp_mro = src->tp_mro;
    Py_RETURN_NONE;
}

static PyMethodDef PatchMROMethods[] = {
    {"patch",  patch_mro, METH_VARARGS,
     "Patch the mro of a class."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef patch_mro_module = {
    PyModuleDef_HEAD_INIT,
    "patch_mro",   /* name of module */
    "",            /* module documentation, may be NULL */
    -1,            /* size of per-interpreter state of the module,
                      or -1 if the module keeps state in global variables. */
    PatchMROMethods
};

PyMODINIT_FUNC
PyInit_patch_mro(void)
{
    return PyModule_Create(&patch_mro_module);
}
