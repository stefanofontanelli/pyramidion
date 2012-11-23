% if form:
${form | n}
% endif
% if result:
<table class="table table-striped table-bordered table-hover">
    <thead>
        % for col in result.cols:
        <th class="${col}">${col}</th>
        % endfor
    </thead>
    <tbody>
    <%
        noresult = True
    %>
    % for row in result.rows():
        <%
            noresult = False
        %>
        <tr>
            % for col in row:
            <td>${col}</td>
            % endfor
        </tr>
    % endfor
    % if noresult:
    <tr><td colspan="${len(result.cols) + 2}">No results.</td></tr>
    % endif
    </tbody>
</table>
<%include file="pyramidion:templates/pagination.mako" args="paginator=result.paginator"/>
% endif