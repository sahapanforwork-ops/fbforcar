# SEO สำหรับ https://impcar.vercel.app

ตรวจเว็บจริงเมื่อ 17 พ.ย. 2569: title, description, canonical, og:image, sitemap และ FAQ ทำไว้ดีแล้วทุกหน้า
**แต่ Google และ AI ยังไม่เก็บเว็บนี้เลย** เพราะติดข้อ 1 ทำ 4 ข้อแรกในโค้ดเว็บ แล้ว deploy (ใช้เวลาประมาณ 5 นาที)

## ต้องแก้ในโค้ดเว็บ

1. **เปิดให้ index** ใน `site.config.json` ตั้ง `launch.allow_indexing` เป็น `true`
   - ตอนนี้ทุกหน้ามี `<meta name="robots" content="noindex, nofollow">` ทำให้ Google, Bing, ChatGPT, Perplexity ไม่เอาเว็บไปแสดง
   - deploy แล้วเช็ก: เปิด view-source หน้าแรก ต้องไม่มีคำว่า `noindex`
2. **เอาค่าตัวอย่างออกจาก JSON-LD** (`AutoRental` ในทุกหน้า) Google มองว่าข้อมูลไม่น่าเชื่อถือ
   - `"email": "hello@impcarrent.example"` ลบทิ้ง หรือใส่อีเมลจริง
   - `"address"` ตอนนี้เป็น `[เลขที่ / ถนน]`, `[เขต]`, `10XXX` ถ้ายังไม่อยากเปิดเผยที่อยู่ ให้เหลือแค่
     `{"@type": "PostalAddress", "addressRegion": "กรุงเทพมหานคร", "addressCountry": "TH"}`
     ถ้ามีจุดรับรถจริง ใส่ที่อยู่จริงพร้อม `geo` ของจุดนั้น
3. **เพิ่มเพจ Facebook ใน `sameAs`** ให้ Google และ AI รู้ว่าเพจกับเว็บเป็นเจ้าเดียวกัน
   ```json
   "sameAs": [
     "https://www.facebook.com/impcarrent",
     "https://line.me/R/ti/p/%40804bunik"
   ]
   ```
4. **วางไฟล์ 2 ไฟล์ในโฟลเดอร์นี้ไว้ที่ root ของเว็บ**
   - `robots.txt` แทนของเดิม: เปิดให้ AI ทุกเจ้าอ่าน (GPTBot, ClaudeBot, PerplexityBot, Google-Extended ฯลฯ) และบอกที่อยู่ sitemap
   - `llms.txt` (ใหม่): สรุปข้อมูลร้านให้ AI อ่าน ราคา รุ่นรถ เงื่อนไข พื้นที่ ช่องทางจอง ทุกตัวเลขมาจากเว็บ ถ้าแก้ราคาหรือเงื่อนไขบนเว็บ ให้แก้ไฟล์นี้ด้วย

## หลัง deploy (เจ้าของร้านทำ ใช้บัญชี Google/Microsoft ของร้าน)

5. **Google Search Console** (search.google.com/search-console)
   - เพิ่ม property แบบ "URL prefix" `https://impcar.vercel.app/` ยืนยันด้วย HTML tag (เอา meta tag ที่ได้ไปใส่ใน `<head>` หน้าแรก)
   - เมนู Sitemaps ส่ง `https://impcar.vercel.app/sitemap.xml`
   - เมนู URL Inspection ใส่ทีละหน้า แล้วกด "Request indexing" (6 หน้า)
6. **Bing Webmaster Tools** (bing.com/webmasters) กด "Import from Google Search Console" ได้เลย
   ChatGPT search และ Copilot ใช้ข้อมูลจาก Bing ข้อนี้สำคัญกับ "ให้ AI แนะนำเว็บ"
7. **Google Business Profile** (business.google.com) สร้างแบบ "ธุรกิจที่ให้บริการตามพื้นที่" ซ่อนที่อยู่ได้
   ใส่ กทม. + 5 จังหวัดปริมณฑล, เวลา 08:00–20:00, เบอร์ 096-219-4138, เว็บ, รูปรถ
   คนค้น "เช่ารถไฟฟ้า ใกล้ฉัน" ใน Google Maps จะเห็นร้าน

## แนะนำเพิ่ม (ไม่บังคับ)

- ใช้โดเมนของร้านเอง เช่น `impcarrent.com` (ปีละประมาณ 400–500 บาท) ผูกกับ Vercel ได้ในเมนู Domains
  ถ้าเปลี่ยน ต้องแก้ canonical, og:url, sitemap, robots.txt และ llms.txt เป็นโดเมนใหม่ แล้วตั้ง redirect 308 จาก vercel.app
- ให้ลูกค้าที่เช่าแล้วรีวิวใน Google Business Profile และเพจ Facebook รีวิวช่วยทั้ง Google Maps และการที่ AI เลือกแนะนำร้าน
