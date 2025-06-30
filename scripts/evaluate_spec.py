import argparse
import json
from pathlib import Path
from typing import Any, Dict

from parser import parse_pdf
from tests.utils import compare_chunks, score_entities, validate_json_data


def load_ground_truth(gt_path: Path) -> Dict[str, Any]:
    with gt_path.open() as f:
        data = json.load(f)
    # Support legacy .fire.json format (list of {page, text} chunks)
    if 'chunks' in data and data['chunks'] and 'page' in data['chunks'][0]:
        data['chunks'] = [
            {
                'title': f"Section {i+1}",
                'start_page': c['page'],
                'end_page': c['page']
            }
            for i, c in enumerate(data['chunks'])
        ]
    return data


def main():
    parser_cli = argparse.ArgumentParser(description="Evaluate a PDF spec against ground truth JSON.")
    parser_cli.add_argument("pdf", type=Path, help="Path to input PDF")
    parser_cli.add_argument("--ground-truth", "-g", type=Path, help="Corresponding .fire.json ground truth file")
    parser_cli.add_argument("--page-tolerance", type=int, default=2)
    args = parser_cli.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    # Derive ground truth path if not provided
    gt_path = args.ground_truth or args.pdf.with_suffix('.fire.json')
    ground_truth = None
    if gt_path.exists():
        ground_truth = load_ground_truth(gt_path)
        if 'chunks' in ground_truth:
            # Validate schema when possible
            try:
                validate_json_data(ground_truth['chunks'], 'chunks')
            except Exception as e:
                print(f"⚠️  Ground truth schema validation failed: {e}")
    else:
        print("⚠️  No ground truth found – only timing & structure checks will be reported.")

    # Parse PDF
    result = parse_pdf(str(args.pdf))

    # Metrics
    metrics = {
        'chunks_found': len(result.chunks),
        'entities_found': len(result.entities),
    }

    report = {
        'pdf': str(args.pdf),
        'metrics': metrics,
        'scores': {},
    }

    if ground_truth and 'chunks' in ground_truth:
        match = compare_chunks(result.chunks, ground_truth['chunks'], page_tolerance=args.page_tolerance)
        report['scores']['chunks_match'] = match
    if ground_truth and 'entities' in ground_truth:
        p, r, f1 = score_entities(result.entities, ground_truth['entities'])
        report['scores']['entities_precision'] = p
        report['scores']['entities_recall'] = r
        report['scores']['entities_f1'] = f1

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main() 