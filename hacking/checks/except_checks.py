#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

# module cannot be called except since that is a reserved word

import ast
import re

from six import PY2

from hacking import core

RE_ASSERT_RAISES_EXCEPTION = re.compile(r"self\.assertRaises\(Exception[,\)]")


@core.flake8ext
def hacking_except_format(logical_line, noqa):
    r"""Check for 'except:'.

    OpenStack HACKING guide recommends not using except:
    Do not write "except:", use "except Exception:" at the very least

    Okay: try:\n    pass\nexcept Exception:\n    pass
    H201: try:\n    pass\nexcept:\n    pass
    H201: except:
    Okay: try:\n    pass\nexcept:  # noqa\n    pass
    """
    if noqa:
        return
    if logical_line.startswith("except:"):
        yield 6, "H201: no 'except:' at least use 'except Exception:'"


@core.flake8ext
def hacking_except_format_assert(logical_line, noqa):
    r"""Check for 'assertRaises(Exception'.

    OpenStack HACKING guide recommends not using assertRaises(Exception...):
    Do not use overly broad Exception type

    Okay: self.assertRaises(NovaException, foo)
    Okay: self.assertRaises(ExceptionStrangeNotation, foo)
    H202: self.assertRaises(Exception, foo)
    H202: self.assertRaises(Exception)
    Okay: self.assertRaises(Exception)  # noqa
    Okay: self.assertRaises(Exception, foo)  # noqa
    """
    if noqa:
        return
    if RE_ASSERT_RAISES_EXCEPTION.search(logical_line):
        yield 1, "H202: assertRaises Exception too broad"


def is_none(node):
    '''Check whether an AST node corresponds to None.

    In Python 2 None uses the same ast.Name class that variables etc. use,
    but in Python 3 there is a new ast.NameConstant class.
    '''
    if PY2:
        return isinstance(node, ast.Name) and node.id == 'None'
    return isinstance(node, ast.NameConstant) and node.value is None


class NoneArgChecker(ast.NodeVisitor):
    '''NodeVisitor to check function calls for None arguments.

    :param func_name: only check calls to functions with this name
    :param num_args:  number of arguments to check for None

    self.none_found will be True if any None arguments were found.
    '''
    def __init__(self, func_name, num_args=2):
        self.func_name = func_name
        self.num_args = num_args
        self.none_found = False

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            local_func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            local_func_name = node.func.id
        else:  # ast.Subscript, etc. -- ignore
            local_func_name = None

        if local_func_name == self.func_name:
            args_to_check = node.args[:self.num_args]
            self.none_found |= any(is_none(x) for x in args_to_check)
        self.generic_visit(node)


@core.flake8ext
@core.off_by_default
def hacking_assert_is_none(logical_line, noqa):
    """Use assertIs(Not)None to check for None in assertions.

    Okay: self.assertEqual('foo', 'bar')
    Okay: self.assertNotEqual('foo', {}.get('bar', None))
    Okay: self.assertIs('foo', 'bar')
    Okay: self.assertIsNot('foo', 'bar', None)
    Okay: foo(self.assertIsNot('foo', 'bar'))
    H203: self.assertEqual(None, 'foo')
    H203: self.assertNotEqual('foo', None)
    H203: self.assertIs(None, 'foo', 'bar')
    H203: self.assertIsNot('foo', None, 'bar')
    H203: foo(self.assertIsNot('foo', None, 'bar'))
    Okay: self.assertEqual(None, 'foo')  # noqa
    Okay: self.assertIs(None, 'foo')  # noqa
    Okay: self.assertIsNone('foo')
    """
    if noqa:
        return
    for func_name in ('assertEqual', 'assertIs', 'assertNotEqual',
                      'assertIsNot'):
        try:
            start = logical_line.index('.%s(' % func_name) + 1
        except ValueError:
            continue
        checker = NoneArgChecker(func_name)
        checker.visit(ast.parse(logical_line))
        if checker.none_found:
            yield start, "H203: Use assertIs(Not)None to check for None"
