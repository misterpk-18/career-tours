import React, { useEffect, useState } from 'react';
import { FileText, Download, ExternalLink, Sparkles, Calendar, CheckCircle, AlertCircle } from 'lucide-react';
import { resumesAPI } from '../services/api';
import Modal from './ui/Modal';
import Alert from './ui/Alert';
import Button from './ui/Button';
import MetricTile from './ui/MetricTile';
import PageSpinner from './ui/PageSpinner';
import SectionLabel from './ui/SectionLabel';
import { formatDate } from '../lib/format';
import { apiErrorMessage } from '../lib/apiError';

export const ResumeViewerModal = ({ isOpen, onClose, resumeId }) => {
  const [resume, setResume] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  // Starts false: with `true` and no resumeId the effect never ran and the
  // spinner stayed up forever.
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen || !resumeId) return undefined;

    let cancelled = false;

    const fetchResumeDetails = async () => {
      // Reset first — otherwise the previous resume's text and download link
      // stay visible while the new one loads.
      setResume(null);
      setPreviewUrl(null);
      setError('');
      setLoading(true);

      try {
        const data = await resumesAPI.getById(resumeId);
        if (cancelled) return;
        setResume(data);

        try {
          const previewData = await resumesAPI.getPreview(resumeId);
          if (!cancelled) setPreviewUrl(previewData.preview_url || data.file_url);
        } catch (err) {
          console.warn('Presigned preview URL failed, falling back to file_url:', err);
          if (!cancelled) setPreviewUrl(data.file_url);
        }
      } catch (err) {
        console.error('Failed to load resume details:', err);
        if (!cancelled) setError(apiErrorMessage(err, 'Unable to load resume details.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchResumeDetails();

    return () => {
      cancelled = true;
    };
  }, [isOpen, resumeId]);

  // Derived from the payload. This was previously hard-coded to
  // "Successfully Extracted" in emerald regardless of whether text existed.
  const hasText = !!resume?.raw_text;

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      title="Review Resume"
      description={resume?.file_name || 'Resume document'}
      icon={FileText}
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
          {previewUrl ? (
            <>
              <Button
                as="a"
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                variant="secondary"
                size="sm"
                icon={ExternalLink}
              >
                Open File Link
              </Button>
              <Button
                as="a"
                href={previewUrl}
                download={resume?.file_name || 'resume'}
                target="_blank"
                rel="noopener noreferrer"
                variant="success"
                size="sm"
                icon={Download}
              >
                Download
              </Button>
            </>
          ) : null}
        </>
      }
    >
      {loading ? (
        <PageSpinner message="Fetching parsed resume details…" className="py-16" />
      ) : error ? (
        <Alert tone="error">{error}</Alert>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <MetricTile
              icon={FileText}
              iconTone="brand"
              label="Document Name"
              value={resume?.file_name || '—'}
            />
            <MetricTile
              icon={Calendar}
              iconTone="accent"
              label="Parsed Date"
              value={formatDate(resume?.parsed_at)}
            />
            <MetricTile
              icon={hasText ? CheckCircle : AlertCircle}
              iconTone={hasText ? 'success' : 'warning'}
              label="Parse Status"
              value={hasText ? 'Text Extracted' : 'No Text Extracted'}
              valueTone={hasText ? 'text-success-fg' : 'text-warning-fg'}
            />
          </div>

          <div>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <SectionLabel icon={Sparkles} iconClassName="text-warning-fg" className="mb-0">
                Parsed Text Extract
              </SectionLabel>
              <span className="text-xs text-fg-muted">
                {resume?.raw_text ? `${resume.raw_text.length} characters` : '0 characters'}
              </span>
            </div>
            {/* break-words matters: whitespace-pre-wrap alone will not break a
                long unbroken token such as a URL, which then overflows. */}
            <div className="mt-2 bg-surface-3 p-4 rounded-xl border border-line text-fg-secondary text-xs font-mono leading-relaxed max-h-64 overflow-auto whitespace-pre-wrap break-words">
              {resume?.raw_text || 'No text extracted from this resume.'}
            </div>
          </div>
        </>
      )}
    </Modal>
  );
};

export default ResumeViewerModal;
