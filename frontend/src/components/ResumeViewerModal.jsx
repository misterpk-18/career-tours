import React, { useState, useEffect } from 'react';
import { resumesAPI } from '../services/api';
import { X, FileText, Download, ExternalLink, Loader2, Sparkles, Calendar, CheckCircle } from 'lucide-react';

export const ResumeViewerModal = ({ isOpen, onClose, resumeId }) => {
  const [resume, setResume] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen && resumeId) {
      fetchResumeDetails();
    }
  }, [isOpen, resumeId]);

  const fetchResumeDetails = async () => {
    setLoading(true);
    setError('');
    try {
      // Get basic resume info
      const data = await resumesAPI.getById(resumeId);
      setResume(data);

      // Attempt preview endpoint if authorized
      try {
        const previewData = await resumesAPI.getPreview(resumeId);
        if (previewData.preview_url) {
          setPreviewUrl(previewData.preview_url);
        }
      } catch (err) {
        console.warn('Presigned preview URL failed, fallback to file_url:', err);
        setPreviewUrl(data.file_url);
      }
    } catch (err) {
      console.error('Failed to load resume details:', err);
      setError('Unable to load resume details.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-3xl glass-panel rounded-2xl p-6 shadow-2xl border border-slate-800 relative max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-button flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Review Resume</h3>
              <p className="text-xs text-slate-400">
                File: <span className="text-brand-300 font-semibold">{resume?.file_name || 'Resume Document'}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="py-4 overflow-y-auto flex-1 space-y-4">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin text-brand-400 mb-3" />
              <p className="text-sm">Fetching parsed resume details...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-950/60 border border-red-800/60 text-red-200 text-sm">
              {error}
            </div>
          ) : (
            <>
              {/* Resume Metadata Badges */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
                  <FileText className="w-5 h-5 text-brand-400" />
                  <div>
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Document Name</div>
                    <div className="text-xs font-semibold text-white truncate max-w-[160px]">{resume?.file_name}</div>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-purple-400" />
                  <div>
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Parsed Date</div>
                    <div className="text-xs font-semibold text-white">
                      {resume?.parsed_at ? new Date(resume.parsed_at).toLocaleDateString() : 'Just now'}
                    </div>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <div>
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Parse Status</div>
                    <div className="text-xs font-semibold text-emerald-400">Successfully Extracted</div>
                  </div>
                </div>
              </div>

              {/* Raw Text Extract Preview */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    Parsed Text Extract
                  </h4>
                  <span className="text-[10px] text-slate-400">
                    {resume?.raw_text ? `${resume.raw_text.length} characters` : '0 characters'}
                  </span>
                </div>
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-slate-300 text-xs font-mono leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap">
                  {resume?.raw_text || 'No text extracted from this resume.'}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="pt-4 border-t border-slate-800 flex items-center justify-between shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            Close
          </button>
          
          {previewUrl && (
            <div className="flex items-center gap-3">
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Open File Link
              </a>
              <a
                href={previewUrl}
                download={resume?.file_name || 'resume'}
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2 rounded-xl gradient-button-emerald text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md"
              >
                <Download className="w-3.5 h-3.5" />
                Download Resume
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResumeViewerModal;
