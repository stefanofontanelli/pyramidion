<%page args="paginator"/>
<div class="pagination pagination-right">
    <ul>
        <%
            window = 2
            first = paginator.first
            previous = paginator.previous
            previous_pages = [page for page in paginator.get_pages(-window)]
            current = paginator.current
            next_pages = [page for page in paginator.get_pages(window)]
            next = paginator.next
            last = paginator.last
        %>
        % if current != first:
        <li>
            <%
                query = dict(start=first.start, limit=first.limit)
                # query.update(export_filters)
            %>
            <a href="${request.current_route_url(_query=query)}">
        % else:
        <li class="disabled">
            <a style="opacity:0.5">
        %endif
                <i class="icon-fast-backward"></i>
            </a>
        </li>
        % if current != previous:
        <li>
            <%
                query = dict(start=previous.start, limit=previous.limit)
                #query.update(export_filters)
            %>
            <a href="${request.current_route_url(_query=query)}">
        % else:
        <li class="disabled">
            <a style="opacity:0.5">
        %endif
                <i class="icon-backward"></i>
            </a>
        </li>
        <%
            if not next_pages:
                length = 2 * window
                previous_pages = [page for page in paginator.get_pages(-length)]
        %>
        % for page in previous_pages:
            <li>
            <%
                query = dict(start=page.start, limit=page.limit)
                #query.update(export_filters)
            %>
            <a href="${request.current_route_url(_query=query)}">
                ${page.number}
            </a>
            </li>
        % endfor
        <li class="active">
            <%
                query = dict(start=current.start, limit=current.limit)
                #query.update(export_filters)
            %>
            <a href="${request.current_route_url(_query=query)}">
                ${current.number}
            </a>
        </li>
        <%
            if not previous_pages:
                length = 2 * window
                next_pages = [page for page in paginator.get_pages(length)]
        %>
        % for page in next_pages:
            <li>
            <%
                query = dict(start=page.start, limit=page.limit)
                #query.update(export_filters)
            %>
            <a href="${request.current_route_url(_query=query)}">
                ${page.number}
            </a>
            </li>
        % endfor
        % if current != next:
        <li>
            <%
                query = dict(start=next.start, limit=next.limit)
                #query.update(export_filters)
            %>
            <a href="${request.current_route_url(_query=query)}">
        % else:
        <li class="disabled">
            <a style="opacity:0.5">
        %endif
                <i class="icon-forward"></i>
            </a>
        </li>
        % if current != last:
        <li>
            <a href="${request.current_route_url(_query=query)}">
        % else:
        <li class="disabled">
            <a style="opacity:0.5">
        %endif
            <%
                query = dict(start=last.start, limit=last.limit)
                #query.update(export_filters)
            %>
                <i class="icon-fast-forward"></i>
            </a>
        </li>
    </ul>
</div>