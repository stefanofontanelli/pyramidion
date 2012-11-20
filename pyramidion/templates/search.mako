% if form:
${form | n}
% endif
% if result:
<table>
<tr>

</tr>
% for row in result.rows():
<tr>
% for col in row:
<td>${col}</td>
% endfor
</tr>
% endfor
</table>

<table id="${routes['search']}" class="table table-striped table-bordered table-hover">
    <thead>
        % for col in result.cols:
        <th class="${col}">${col}</th>
        % endfor
        % if update_button and delete_button:
        <th colspan="2"></th>
        % elif update_button or delete_button:
        <th></th>
        % endif
    </thead>
    <tbody>
        % for item in items:
        <%
            dict_ = {}
            for col in cols:
                
                obj = item
                
                for name in col.split('.'):
                    obj = getattr(obj, name, None)

                dict_[col] = obj
        %>
        <tr ${' '.join([unicode('item-{}="{}"').format(col.replace('.', '-'), value)
                        for col, value in dict_.items()]) | n}>
            % for col in cols:
            <td class="${col}">${dict_[col] or ''}</td>
            % endfor
            % if update_button:
            <td class="btncol">
                <a class="btn btn-info" href="${request.route_url(routes['update'],
                                                                  **{pkey: getattr(item, pkey)})}">
                    <i class="icon-pencil icon-white"></i>
                </a>
            </td>
            % endif
            % if delete_button:
            <td class="btncol">
                <a class="btn btn-danger" href="${request.route_url(routes['delete'],
                                                                  **{pkey: getattr(item, pkey)})}">
                    <i class="icon-trash icon-white"></i>
                </a>
            </td>
            % endif
        </tr>
        % endfor
        % if not items:
        <tr><td colspan="${len(cols) + 2}">No results.</td></tr>
        % endif
    </tbody>
</table>
<%include file="pyramidion:templates/pagination.mako"/>
% endif