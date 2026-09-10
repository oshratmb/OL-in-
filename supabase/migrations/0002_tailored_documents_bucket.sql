-- Phase 2: private storage for generated tailored resumes/cover-letter docx files.

insert into storage.buckets (id, name, public)
values ('tailored-documents', 'tailored-documents', false)
on conflict (id) do nothing;

create policy "own tailored documents: all" on storage.objects for all
  using (bucket_id = 'tailored-documents' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'tailored-documents' and (storage.foldername(name))[1] = auth.uid()::text);
