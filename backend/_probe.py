import asyncio, json
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.db.init_db import init_db
from app.db.session import get_db
from app.main import create_app
from app.services.catalog_sync import CatalogSyncService

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    await init_db(engine)
    sf = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as session:
        with open("tests/fixtures/anilist_page1.json") as f: p1 = json.load(f)
        with open("tests/fixtures/anilist_page2.json") as f: p2 = json.load(f)
        items=[]
        for item in (p1["data"]["Page"]["media"] + p2["data"]["Page"]["media"]):
            title = item.get("title") or {}
            cover = item.get("coverImage") or {}
            studios = (item.get("studios") or {}).get("nodes") or []
            main = studios[0].get("name") if studios else None
            from app.core.text import strip_html_tags
            items.append({
                "id": item["id"], "id_mal": item.get("idMal"),
                "title_romaji": title.get("romaji"), "title_english": title.get("english"),
                "title_native": title.get("native"), "synonyms": item.get("synonyms") or [],
                "description": strip_html_tags(item.get("description")),
                "cover_image_url": cover.get("extraLarge") or cover.get("large"),
                "banner_image_url": item.get("bannerImage"), "format": item.get("format"),
                "episodes": item.get("episodes"), "duration": item.get("duration"),
                "status": item.get("status"), "season": item.get("season"),
                "season_year": item.get("seasonYear"), "average_score": item.get("averageScore"),
                "popularity": item.get("popularity") or 0, "is_adult": bool(item.get("isAdult", False)),
                "source": item.get("source"), "main_studio": main,
                "updated_at_anilist": item.get("updatedAt"),
                "genres": [g for g in item.get("genres") or [] if g],
                "tags": [{"name": t["name"], "category": t.get("category"), "is_adult": bool(t.get("isAdult", False)), "rank": int(t.get("rank") or 0)} for t in item.get("tags") or [] if t.get("name")],
            })
        await CatalogSyncService().upsert_batch(session, items)
        await session.commit()

    app = create_app()
    async def override_get_db():
        async with sf() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # register
        r = await c.post("/api/auth/register", json={"email":"a@example.com","password":"valid_secure_password_1","display_name":"A"})
        print("register", r.status_code, r.json())
        # list empty
        r = await c.get("/api/list")
        print("list empty", r.status_code, r.json())
        # create entry
        r = await c.put("/api/list/154587", json={"status":"completed","rating":9})
        print("create", r.status_code, json.dumps(r.json())[:300])
        # create entry for mature
        r = await c.put("/api/list/113425", json={"status":"planning"})
        print("create mature", r.status_code, r.json())
        # list
        r = await c.get("/api/list")
        print("list", r.status_code, json.dumps(r.json())[:400])
        # invalid rating
        r = await c.put("/api/list/154587", json={"rating":11})
        print("rating 11", r.status_code, r.json())
        r = await c.put("/api/list/154587", json={"rating":0})
        print("rating 0", r.status_code, r.json())
        r = await c.put("/api/list/154587", json={"rating":5.5})
        print("rating float", r.status_code, r.json())
        r = await c.put("/api/list/154587", json={"status":"invalid"})
        print("bad status", r.status_code, r.json())
        r = await c.put("/api/list/999999", json={"status":"planning"})
        print("unknown anime", r.status_code, r.json())
        # update
        r = await c.put("/api/list/154587", json={"status":"watching"})
        print("update", r.status_code, r.json())
        # delete
        r = await c.delete("/api/list/154587", headers={"X-CSRF-Token": r.request.headers.get("x-csrf-token","")})
        print("delete", r.status_code, r.json())
        # recs/me empty
        r = await c.get("/api/recs/me")
        print("recs/me empty", r.status_code, r.json())
        # taste profile
        r = await c.put("/api/auth/me/taste-profile", json={"quiz_answers":{"mood":"cozy"},"liked_ids":[154587,16498,113425,1535,9253]}, headers={"X-CSRF-Token": r2 if False else ""})
        print("taste", r.status_code, r.json())

asyncio.run(main())
