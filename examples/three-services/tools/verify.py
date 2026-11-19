"""Repeatable baseline and feature acceptance over real HTTP, with synthetic fixtures."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services import services

API = "/ops/api/v1/campaigns"
IDS = ["A101", "A102", "A103", "A104"]
OLD_ITEMS = [
    {"id": "A101", "name": "春季活动", "status": "DRAFT"},
    {"id": "A102", "name": "春季上新", "status": "ACTIVE"},
    {"id": "A103", "name": "夏季上新", "status": "ACTIVE"},
    {"id": "A104", "name": "春季复盘", "status": "ENDED"},
]


def expect(actual, expected):
    if actual != expected:
        raise AssertionError(f"Expected {expected!r}, got {actual!r}")


def request(origin, path, tenant="a"):
    headers = {"Authorization": "Bearer demo-tenant-" + tenant} if tenant else {}
    try:
        with urlopen(Request(origin + path, headers=headers), timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        with error:
            return error.code, json.load(error)


def listing(urls, **query):
    status, body = request(urls["web"], API + "?" + urlencode(query))
    expect(status, 200)
    return body


def run(projects, stage):
    results = []
    def case(ac_id, title, body):
        actual = body()
        results.append({"id": ac_id, "name": title, "status": "PASS", "actual": actual})
        print(f"PASS {ac_id} {title}", flush=True)

    with services(projects) as urls:
        def baseline():
            old = request(urls["web"], API)
            expect(old, (200, {"items": OLD_ITEMS, "total": 4}))
            single = request(urls["capacity"], "/internal/capacities/A102")
            expect(single, (200, {"id": "A102", "capacity": 10, "reserved": 7}))
            no_auth = request(urls["campaign"], API, tenant=None)
            expect(no_auth[0], 401)
            return {"legacy": old, "single": single, "without_identity": no_auth[0]}
        if stage == "baseline":
            case("BASE", "三个服务可运行且旧调用兼容", baseline)
            return results

        def batch():
            reply = request(urls["capacity"], "/internal/capacities?ids=" + ",".join(IDS))
            expect(reply, (200, {"items": [
                {"id": "A101", "remaining": 10}, {"id": "A102", "remaining": 3},
                {"id": "A103", "remaining": 0}, {"id": "A104", "remaining": 0},
            ]}))
            single = request(urls["capacity"], "/internal/capacities/A102")
            expect(single, (200, {"id": "A102", "capacity": 10, "reserved": 7}))
            return {"batch": reply[1], "legacy_single": single[1]}
        case("AC01", "批量名额、零下限及旧单活动接口", batch)

        def aggregate():
            body = listing(urls, includeAvailability="true")
            expect([item["id"] for item in body["items"]], IDS)
            expect([item["remaining"] for item in body["items"]], [10, 3, 0, 0])
            expect([item["bookable"] for item in body["items"]], [False, True, False, False])
            expect(body["total"], 4)
            return body
        case("AC02", "后端一通过真实 HTTP 聚合后端二", aggregate)

        def pagination():
            first = listing(urls, bookable="true", pageSize=1, page=1)
            second = listing(urls, bookable="true", pageSize=1, page=2)
            expect([item["id"] for item in first["items"]], ["A102"])
            expect(first["total"], 1)
            expect(second, {"items": [], "total": 1})
            return {"first": first, "second": second}
        case("AC03", "过滤发生在分页前且总数一致", pagination)

        def intersection():
            spring = listing(urls, keyword="春季", status="ACTIVE", bookable="true")
            summer = listing(urls, keyword="夏季", bookable="true")
            expect([item["id"] for item in spring["items"]], ["A102"])
            expect(spring["total"], 1)
            expect(summer, {"items": [], "total": 0})
            return {"spring": spring, "summer": summer}
        case("AC04", "关键词状态和可报名条件取交集", intersection)
        case("AC05", "默认列表保留原字段和计数", baseline)

        def isolation():
            query = API + "?includeAvailability=true"
            tenant_b = request(urls["campaign"], query, tenant="b")
            expect(tenant_b[0], 200)
            expect(tenant_b[1]["items"], [
                {"id": "B105", "name": "春季跨区", "status": "ACTIVE", "remaining": 39, "bookable": True}
            ])
            expect(tenant_b[1]["total"], 1)
            mixed = request(urls["capacity"], "/internal/capacities?ids=A102,B105")
            expect(mixed[0], 404)
            no_auth = request(urls["capacity"], "/internal/capacities?ids=A102", tenant=None)
            expect(no_auth[0], 401)
            invalid = {}
            for query in ("bookable=maybe", "includeAvailability=", "bookable=true&bookable=false"):
                response = request(urls["campaign"], API + "?" + query)
                expect(response[0], 400)
                expect(response[1]["error"]["code"], "INVALID_QUERY")
                invalid[query] = response[0]
            invalid_capacity = request(urls["capacity"], "/internal/capacities?ids=")
            expect(invalid_capacity[0], 400)
            return {"tenant_b": tenant_b[1], "mixed_tenants": mixed[0],
                    "without_identity": no_auth[0], "invalid_queries": invalid}
        case("AC06", "租户隔离、身份和新参数校验", isolation)

    def dependency():
        actual = {}
        for mode in ("offline", "malformed"):
            with services(projects, capacity_mode=mode) as urls:
                response = request(urls["web"], API + "?bookable=true")
                expect(response[0], 503)
                expect(response[1]["error"]["code"], "DEPENDENCY_UNAVAILABLE")
                legacy = request(urls["web"], API)
                expect(legacy, (200, {"items": OLD_ITEMS, "total": 4}))
                actual[mode] = {"feature": response, "legacy": legacy}
        return actual
    case("AC07", "依赖失败时受控报错且旧查询仍可用", dependency)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("projects", type=Path)
    parser.add_argument("--stage", choices=("baseline", "feature"), default="feature")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = run(args.projects.resolve(), args.stage)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(results)} checks passed ({args.stage})")
