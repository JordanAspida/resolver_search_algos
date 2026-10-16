from .common import cached, store
from .formSearch import search as search_forms


LABEL = "Reports"


def search(client):

    if result := cached(client, "reports"):
        return result
    
    reports = {report.id: report for report in client.reports.get_all_reports()}
    paths = {}
    used_ids = set()

    for application in client.applications.get_all_applications():
        for activity in client.applications.get_activities(application.id):
            for view in client.applications.get_views(application.id, activity.id):
                report_id = view.reportId
                if report_id is not None:
                    used_ids.add(report_id)
                    paths.setdefault(report_id, set()).add(
                        f"App: {application.name} → Activity: {activity.name} → View: {view.name}")
                    
    used_forms, _ = search_forms(client)
    for form in used_forms:
        # Maybe need to check NAV forms too?
        for report in client.forms.get_form_reports(form["id"]):
            used_ids.add(report.id)
            paths.setdefault(report.id, set()).add(f"Form: {form["name"]} → Report: {report.name}")

    used = [{**reports[report_id].model_dump(), "path": " | ".join(sorted(paths.get(report_id, [])))}
            for report_id in used_ids if report_id in reports]
    unused = [report for report_id, report in reports.items() if report_id not in used_ids]
    
    return store(client, "reports", (used, unused))
