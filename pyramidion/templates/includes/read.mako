<%page args="title, form, values"/>
<ul class="nav nav-tabs">
    <li class="active">
        <a href="#item">${title}</a>
    </li>
</ul>
<div class="tab-pane">
    ${form.render(values) | n}
</div>
<script language="javascript">
jQuery(document).ready(function () {
    jQuery('input').attr("disabled", "disabled");
    jQuery('select').attr("disabled", "disabled");
    jQuery('textarea').attr("disabled", "disabled");
});
</script>