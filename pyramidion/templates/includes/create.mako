<%page args="title, form, values, error"/>
<ul class="nav nav-tabs">
    <li class="active">
        <a href="#items">${title}</a>
    </li>
</ul>
<div class="tab-pane">
    % if not error:
    ${form.render(values) | n}
    % else:
    ${error.render() | n}
    % endif
</div>