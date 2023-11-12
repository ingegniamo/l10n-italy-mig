import glob
import xml.etree.ElementTree as ET
import json
import html
import json

NOT_OPERATOR = '!'
OR_OPERATOR = '|'
AND_OPERATOR = '&'
DOMAIN_OPERATORS = (NOT_OPERATOR, OR_OPERATOR, AND_OPERATOR)
TRUE_LEAF = (1, '=', 1)
FALSE_LEAF = (0, '=', 1)

TRUE_DOMAIN = [TRUE_LEAF]
FALSE_DOMAIN = [FALSE_LEAF]
def is_boolean(element):
    return element == TRUE_LEAF or element == FALSE_LEAF
def is_operator(element):
    """ Test whether an object is a valid domain operator. """
    return isinstance(element, str) and element in DOMAIN_OPERATORS
def _tree_as_domain(tree):
    """ Return the domain list represented by the given domain tree. """
    def _flatten(tree):
        if tree[0] == '?':
            yield TRUE_LEAF if tree[1] else FALSE_LEAF
        elif tree[0] == '!':
            yield tree[0]
            yield from _flatten(tree[1])
        elif tree[0] in ('&', '|'):
            yield from tree[0] * (len(tree) - 2)
            for subtree in tree[1:]:
                yield from _flatten(subtree)
        elif tree[0] in ('any', 'not any'):
            yield (tree[1], tree[0], _tree_as_domain(tree[2]))
        else:
            yield (tree[1], tree[0], tree[2])

    return list(_flatten(tree))
def _tree_from_domain(domain):
    """ Return the domain as a tree, with the following structure::

        <tree> ::= ('?', <boolean>)
                |  ('!', <tree>)
                |  ('&', <tree>, <tree>, ...)
                |  ('|', <tree>, <tree>, ...)
                |  (<comparator>, <fname>, <value>)

    By construction, AND (``&``) and OR (``|``) nodes are n-ary and have at
    least two children.  Moreover, AND nodes (respectively OR nodes) do not have
    AND nodes (resp. OR nodes) in their children.
    """
    stack = []
    for item in reversed(domain):
        if item == '!':
            stack.append(_tree_not(stack.pop()))
        elif item == '&':
            stack.append(_tree_and((stack.pop(), stack.pop())))
        elif item == '|':
            stack.append(_tree_or((stack.pop(), stack.pop())))
        elif item == TRUE_LEAF:
            stack.append(('?', True))
        elif item == FALSE_LEAF:
            stack.append(('?', False))
        else:
            lhs, comparator, rhs = item
            if comparator in ('any', 'not any'):
                rhs = _tree_from_domain(rhs)
            stack.append((comparator, lhs, rhs))
    return _tree_and(reversed(stack))
def _tree_not(tree):
    """ Negate a tree node. """
    if tree[0] == '?':
        return ('?', not tree[1])
    if tree[0] == '!':
        return tree[1]
    if tree[0] == '&':
        return ('|', *(_tree_not(item) for item in tree[1:]))
    if tree[0] == '|':
        return ('&', *(_tree_not(item) for item in tree[1:]))
    if tree[0] in TERM_OPERATORS_NEGATION:
        return (TERM_OPERATORS_NEGATION[tree[0]], tree[1], tree[2])
    return ('!', tree)


def _tree_and(trees):
    """ Return the tree given by AND-ing all the given trees. """
    children = []
    for tree in trees:
        if tree == ('?', True):
            pass
        elif tree == ('?', False):
            return tree
        elif tree[0] == '&':
            children.extend(tree[1:])
        else:
            children.append(tree)
    if not children:
        return ('?', True)
    if len(children) == 1:
        return children[0]
    return ('&', *children)


def _tree_or(trees):
    """ Return the tree given by OR-ing all the given trees. """
    children = []
    for tree in trees:
        if tree == ('?', True):
            return tree
        elif tree == ('?', False):
            pass
        elif tree[0] == '|':
            children.extend(tree[1:])
        else:
            children.append(tree)
    if not children:
        return ('?', False)
    if len(children) == 1:
        return children[0]
    return ('|', *children)
class converti(object):
        def __init__(self, domain):
            self.expression = domain
            
        def parse(self):
            def pop():
                """ Pop a leaf to process. """
                return stack.pop()

            def push(leaf):
                """ Push a leaf to be processed right after. """

                stack.append((leaf))

            def pop_result():
                return result_stack.pop()

            def push_result(sql):
                result_stack.append(sql)

            # process domain from right to left; stack contains domain leaves, in
            # the form: (leaf, corresponding model, corresponding table alias)
            stack = []
            for leaf in self.expression:
                push(leaf)
            #print(stack)

            # stack of SQL expressions
            result_stack = []
            
            while stack:
                
                # Get the next leaf to process
                leaf = pop()
                
                # ----------------------------------------
                # SIMPLE CASE
                # 1. leaf is an operator
                # 2. leaf is a true/false leaf
                # -> convert and add directly to result
                # ----------------------------------------
               # print(leaf)
                if is_operator(leaf):
                    #print(stack)
                    if leaf == NOT_OPERATOR:
                        push_result(("(not (%s))" % pop_result()))
                    elif leaf == AND_OPERATOR:
                        push_result(("(%s and %s)" % (pop_result(), pop_result())))
                    else:
                        push_result(("(%s or %s)" % (pop_result(), pop_result())))
                    continue

                if is_boolean(leaf):
                    #print(leaf)
                    push_result(leaf)
                    continue
                left, operator, right = leaf
                if isinstance(right,str) :
                    right = json.dumps(right)
                if operator == "=":
                    operator = "=="
                push_result("%s %s %s" %(left,operator,right))

            return result_stack
                
# test = _tree_from_domain(test)
# test = _tree_as_domain(test)
# test = converti(test)
# print(test.parse()[0])
# exit()
views = glob.glob("**/*.xml",recursive=True)
for view in views:
    
    file = ET.parse(view)
    
    root = file.getroot()
    attrs_fields =root.findall(".//*[@attrs]")
    attrs_extend_parent_fields = root.findall(".//attribute[@name='attrs']/..")
    states_fields = root.findall(".//*[@states]")
    if states_fields:
        for state_field in states_fields:
            states = state_field.attrib.get('states')
            states = states.split(",")
            states = ["'%s'" % state for state in states]
            state_field.set("invisible","state not in (%s)"% ",".join(states))
            del state_field.attrib['states']
        string = ET.tostring(root).decode('utf-8')
        file = open(view,"w")
        file.write(string)
        file.close()
        

    if attrs_extend_parent_fields:
        print(view)
        for parent in attrs_extend_parent_fields:
            attrs_extend_fields = parent.findall(".//attribute[@name='attrs']")
           
            for attrs_extend_element in attrs_extend_fields:
                content = html.unescape(attrs_extend_element.text.strip())
                attr_content = eval(content)
                
                for attr in attr_content:
                    obj = converti(attr_content[attr])
                    value=attr_content[attr]
                    
                    element = ET.SubElement(parent, 'attribute')
                    element.set("name",attr)

                    element.text = str(obj.parse())
                attrs_extend_element.text
                parent.remove(attrs_extend_element)


        string = ET.tostring(root).decode('utf-8')
        file = open(view,"w")
        file.write(string)
        file.close()
        
       # break;
    #exit    
    
    if attrs_fields:
        for field in attrs_fields:
            attrs = field.attrib.get('attrs')
            attrs = html.unescape(attrs)
            attrib_list = eval(attrs)
            for attr in attrib_list:
                
                value=attrib_list[attr]
                obj = converti(value)
                field.set(attr,str(obj.parse()[0]))
                #print(value)
            del field.attrib['attrs']
        print(view)
        string = ET.tostring(root).decode('utf-8')
        file = open(view,"w")
        file.write(string)
        file.close()
        
        #break
        
            
           
            #print(attrib_list)
            