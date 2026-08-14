from pathlib import Path
from PIL import Image, ImageFilter
from backend.analysis import analyze_print_job
from backend.quality_gate import evaluate_quality

def test_90x120_canvas_requires_real_4x(tmp_path:Path):
    src=tmp_path/"source.jpg"; Image.new("RGB",(1024,1536),"white").save(src); plan=analyze_print_job(src,width=90,height=120,unit="cm",material="canvas")
    assert plan.target_ppi==100; assert plan.target_width_px==3543; assert plan.target_height_px==4724; assert 3.4<plan.scale_needed<3.5; assert plan.upscale_factor==4; assert plan.can_reach_target_with_4x is True

def test_source_too_small_for_single_safe_pass(tmp_path:Path):
    src=tmp_path/"tiny.jpg"; Image.new("RGB",(400,400),"white").save(src); plan=analyze_print_job(src,width=200,height=200,unit="cm",material="canvas")
    assert plan.scale_needed>4; assert plan.upscale_factor==0; assert plan.can_reach_target_with_4x is False

def test_quality_gate_rejects_blur(tmp_path:Path):
    src=tmp_path/"source.png"; cand=tmp_path/"candidate.png"; image=Image.new("RGB",(512,512),"white")
    for x in range(0,512,16):
        for y in range(512): image.putpixel((x,y),(0,0,0))
    for y in range(0,512,16):
        for x in range(512): image.putpixel((x,y),(0,0,0))
    image.save(src); image.resize((2048,2048),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(12)).save(cand); report=evaluate_quality(src,cand,min_edge_ratio=0.9); assert report.passed is False; assert report.edge_ratio<0.9
