<%block name="status">
% if request.response.status_int == 201:
    ${request.response.status} OK
% else:
    ${request.response.status}
% endif
</%block>
<%block name="message">
% if form:
${form | n}
% endif
</%block>