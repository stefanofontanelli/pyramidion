<%page args="request, routes, title, form, values, cols, items, attrs, key, no_result_text, error, create_button=True, update_button=True, delete_button=True"/>
<ul class="nav nav-tabs">
    <li class="active">
        <a href="#items">${title}</a>
    </li>
</ul>
<div class="tab-pane">
    <p class="button-group">
        % if create_button:
        <a class="btn btn-success" href="${request.route_url(routes['create'])}">
            <i class="icon-plus icon-white"></i> Nuovo
        </a>
        % endif
        <a class="btn btn-primary" href="#search-form" data-toggle="modal">
            <i class="icon-search icon-white"></i> Ricerca
        </a>
    </p>
    <div id="search-form" class="modal hide fade">
        <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-hidden="true">
                &times;
            </button>
            <h3>Ricerca: ${title}</h3>
        </div>
        <div class="modal-body">
            % if not error:
                ${form.render(values) | n}
            % else:
                ${error.render() | n}
            % endif
        </div>
        <div class="modal-footer">
            <a href="#" class="btn" data-dismiss="modal">Close</a>
        </div>
    </div>
    <table class="table table-striped table-bordered table-hover">
        <thead>
            <tr>
                % for col in cols:
                <th>${col}</th>
                % endfor
                <th colspan="2"></th>
            </tr>
        </thead>
        <tbody>
            % for item in items:
            <tr>
                % for attr in attrs:
                <td>${getattr(item, attr)}</td>
                % endfor
                <td class="btncol">
                    % if update_button:
                    <a class="btn btn-info" href="${request.route_url(routes['update'],
                                                                      **{key: getattr(item, key)})}">
                        <i class="icon-pencil icon-white"></i>
                    </a>
                    % endif
                </td>
                <td class="btncol">
                    % if delete_button:
                    <a class="btn btn-danger" href="${request.route_url(routes['delete'],
                                                                      **{key: getattr(item, key)})}">
                        <i class="icon-trash icon-white"></i>
                    </a>
                    % endif
                </td>
            </tr>
            % endfor
            % if not items:
            <tr><td colspan="${len(cols) + 2}">${no_result_text}</td></tr>
            % endif
        </tbody>
    </table>
    <div class="pagination pagination-right">
        <ul>
            <li class="disabled"><a href="#">&laquo;</a></li>
            <li class="active"><a href="#">1</a></li>
            <li><a href="#">2</a></li>
            <li><a href="#">3</a></li>
            <li><a href="#">4</a></li>
            <li><a href="#">&raquo;</a></li>
        </ul>
    </div>
</div>