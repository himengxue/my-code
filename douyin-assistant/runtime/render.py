"""Portable, original typography video renderer. No paid API or account required."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def ffmpeg_exe():
    found=shutil.which('ffmpeg')
    if found:return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def font_path():
    for candidate in [os.environ.get('DOUYIN_FONT',''),r'C:\Windows\Fonts\msyh.ttc',r'C:\Windows\Fonts\simhei.ttf','/System/Library/Fonts/PingFang.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        if candidate and Path(candidate).is_file():return candidate
    raise ValueError('找不到中文字体；用 DOUYIN_FONT 指定本地字体文件')


def lines_for(draw,text,font,width):
    lines=[]
    for para in text.splitlines():
        line=''
        for char in para:
            if line and draw.textlength(line+char,font=font)>width:
                lines.append(line);line=char
            else:line+=char
        lines.append(line)
    return lines


def render(storyboard_path, output_dir):
    source=Path(storyboard_path).resolve();story=json.loads(source.read_text(encoding='utf-8-sig'))
    scenes=story.get('scenes',[])
    if not story.get('title') or not 2<=len(scenes)<=12:
        raise ValueError('分镜需要 title 和 2–12 个 scenes')
    out=Path(output_dir).resolve()
    if out.exists():raise ValueError('输出目录必须不存在，防止覆盖原素材')
    W,H=720,1280;font=font_path(); cards=[]
    # Validate all text layouts before writing anything.
    for index,scene in enumerate(scenes):
        duration=float(scene.get('duration',6))
        if not 2<=duration<=30:raise ValueError('每段时长须为 2–30 秒')
        image=Image.new('RGB',(W,H));px=image.load()
        for y in range(H):
            c=(13+int(9*y/H),20+int(14*y/H),34+int(28*y/H))
            for x in range(W):px[x,y]=c
        draw=ImageDraw.Draw(image)
        accent=(112,232,204)
        draw.rounded_rectangle((56,78,160,86),radius=4,fill=accent)
        small=ImageFont.truetype(font,24);head=ImageFont.truetype(font,54);body=ImageFont.truetype(font,34)
        draw.text((56,110),f'{index+1:02d} / {len(scenes):02d}   原创 · AI 创作',font=small,fill=(159,184,199))
        headings=lines_for(draw,str(scene.get('headline','')),head,W-112)
        bodylines=lines_for(draw,str(scene.get('body','')),body,W-112)
        if not any(headings) or len(headings)>3 or len(bodylines)>14:
            raise ValueError('分镜文字过长或标题为空；请精简每张卡片内容')
        y=240
        for line in headings:draw.text((56,y),line,font=head,fill=(245,247,250));y+=79
        y+=60
        for line in bodylines:draw.text((56,y),line,font=body,fill=(198,216,228));y+=55
        if y>1100:raise ValueError('分镜文字超出安全区域，请拆成更多场景')
        draw.line((56,1164,W-56,1164),fill=(55,75,91),width=2)
        footer=str(story.get('series','原创观察'))[:20]
        draw.text((56,1190),footer,font=small,fill=accent)
        cards.append((image,duration))
    out.mkdir(parents=True)
    exe=ffmpeg_exe();segments=[]
    for index,(image,duration) in enumerate(cards):
        card=out/f'scene-{index+1:02d}.png';video=out/f'scene-{index+1:02d}.mp4';image.save(card)
        # Each segment uses the same encoding, permitting lossless concatenation.
        fade=f'fade=t=in:st=0:d=0.25,fade=t=out:st={duration-0.25}:d=0.25'
        command=[exe,'-nostdin','-hide_banner','-loglevel','error','-loop','1','-i',str(card),'-t',str(duration),'-vf',fade,'-r','25','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-an',str(video)]
        subprocess.run(command,check=True,capture_output=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));segments.append(video)
    listing=out/'concat.txt';listing.write_text(''.join("file '"+p.name+"'\n" for p in segments),encoding='utf-8')
    result=out/'video.mp4'
    subprocess.run([exe,'-nostdin','-hide_banner','-loglevel','error','-f','concat','-safe','1','-i',str(listing),'-c','copy','-movflags','+faststart',str(result)],check=True,capture_output=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    subprocess.run([exe,'-nostdin','-v','error','-i',str(result),'-f','null','-'],check=True,capture_output=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    shutil.copy2(out/'scene-01.png',out/'cover.png')
    caption=str(story.get('caption') or story['title'])
    (out/'caption.txt').write_text(caption+'\n',encoding='utf-8')
    manifest={'topic':story.get('topic',story['title']),'title':story['title'],'video':'video.mp4','cover':'cover.png','caption_file':'caption.txt','ai_generated':True,'visibility':'public','style':'original_typography','audio':'silent'}
    (out/'publish.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'video':str(result),'cover':str(out/'cover.png'),'manifest':str(out/'publish.json'),'duration':sum(x[1] for x in cards),'dimensions':[W,H],'audio':'silent','full_decode':'passed','published':False}
