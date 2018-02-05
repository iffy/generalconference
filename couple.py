import sys
import io
from jinja2 import Environment
import markdown
import yaml

metadata = sys.argv[1]
file1 = sys.argv[2]
file2 = sys.argv[3]

with io.open(metadata, 'r') as m, io.open(file1, 'r') as f1, io.open(file2, 'r') as f2:
    meta = yaml.load(m)
    guts1 = f1.read()
    para1 = guts1.split('\n\n')
    guts2 = f2.read()
    para2 = guts2.split('\n\n')
    
    para1 = para1[:para1.index('## References')]
    para2 = para2[:para2.index('## References')]

    zipped = zip(para1, para2)

template = '''
<html>
<head>
<style>
h1 {
    font-size: 16pt;
    margin: 0;
}
table td {
    padding: 0 12px 12px 0;
    vertical-align: top;
    width: 50%;
}
p {
    margin: 0;
}
</style>
</head>
<body>
<table>
<tr>
    <td colspan="2">
        {{ meta.title }}
        &mdash; {{ meta.speaker }}
        &mdash; {{ meta.session_title }} {{ meta.month }}/{{ meta.year }}
    </td>
</tr>
{% for pair in pairs %}
<tr>
    <td class="first">{{ pair[0]|markdown }}</td>
    <td class="second">{{ pair[1]|markdown }}</td>
</tr>
{% endfor %}
</table>
</body>
</html>
'''

env = Environment()
env.filters['markdown'] = markdown.markdown

t = env.from_string(template)
print t.render(pairs=zipped, meta=meta).encode('utf-8')