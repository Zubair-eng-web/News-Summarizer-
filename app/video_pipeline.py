import time

from app.agents.summarizer import get_client
from app.agents.video_agent import summarize_video
from app.collectors.youtube import TranscriptError, collect_videos, fetch_transcript
from app.core.storage import get_known_video_ids, save_videos
from app.core.video import VideoSummary


def run_video_pipeline(
    limit_per_channel: int = 2,
    max_videos: int = 5,
    only_new: bool = True,
    client=None,
    collector=collect_videos,
    transcript_fetcher=fetch_transcript,
    known_ids_loader=get_known_video_ids,
    saver=save_videos,
    delay: float = 4.0,
) -> list[VideoSummary]:
    """Collect -> naye videos -> transcript -> summary -> DB."""
    videos = collector(limit_per_channel)
    known = known_ids_loader() if only_new else set()
    fresh = [v for v in videos if v.video_id not in known][:max_videos]
    print(f"Videos mile: {len(videos)} | Naye (summary baaqi): {len(fresh)}")
    if not fresh:
        return []

    client = client or get_client()
    results: list[VideoSummary] = []
    for i, video in enumerate(fresh):
        try:
            transcript = transcript_fetcher(video.video_id)
        except TranscriptError as e:
            print(f"[WARN] Transcript nahi mila ({video.channel}): {e}")
            transcript = None
        results.append(summarize_video(video, transcript, client))
        if delay and i < len(fresh) - 1:
            time.sleep(delay)  # free tier ki rate limit se bachne ke liye

    saver(results)
    return results


if __name__ == "__main__":
    import sys

    only_new = "--again" not in sys.argv
    results = run_video_pipeline(max_videos=3, only_new=only_new)

    print(f"\nTotal summaries: {len(results)}\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. [{r.channel}] {r.title}  (transcript: {'haan' if r.has_transcript else 'nahi'})")
        print(f"   Summary: {r.summary}")
        for p in r.key_points:
            print(f"   - {p}")
        if r.takeaway:
            print(f"   Takeaway: {r.takeaway}")
        print(f"   {r.link}\n")
