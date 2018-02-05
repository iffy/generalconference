#!/usr/bin/env python
import click
import os
import io
import subprocess

@click.command()
@click.option('-d', '--data-dir',
    default='data')
@click.option('-m', '--month',
    type=str)
@click.option('-y', '--year',
    type=int)
@click.option('-o', '--output-dir',
    default='output')
@click.argument('lang1')
@click.argument('lang2')
def run(data_dir, lang1, lang2, month, year, output_dir):
    date_key = '{year}-{month}'.format(**locals())
    output_root = os.path.join(output_dir, '{0}-{1}-{2}'.format(lang1, lang2, date_key))
    lang1_root = os.path.join(data_dir, lang1, date_key)
    lang2_root = os.path.join(data_dir, lang2, date_key)
    talks = os.listdir(lang1_root)
    pdf_filenames = []
    for talk in talks:
        if not os.path.isdir(os.path.join(lang1_root, talk)):
            continue
        print talk
        dst_dir = os.path.join(output_root, talk)
        print dst_dir
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)

        html_filename = os.path.join(dst_dir, 'text.html')
        with io.open(html_filename, 'w') as html_fh:
            subprocess.check_call(['python', 'couple.py',
                os.path.join(lang1_root, talk, 'metadata.yml'),
                os.path.join(lang1_root, talk, 'text.md'),
                os.path.join(lang2_root, talk, 'text.md')],
                stdout=html_fh)

        pdf_filename = os.path.join(dst_dir, 'text.pdf')
        subprocess.check_call([
            'prince',
            html_filename,
            '-o',
            pdf_filename,
        ])
        pdf_filenames.append(pdf_filename)

    agg_filename = os.path.join(output_root, 'all.pdf')
    print ''
    print 'To combine the PDFs do:'
    print ''
    print '    pdfunite {0}/*/*.pdf {1}'.format(output_root, agg_filename)
    print ''


if __name__ == '__main__':
    run()
