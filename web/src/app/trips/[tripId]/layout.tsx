import TripShell from '@/components/fe2/TripShell'

export default async function TripLayout({ children, params }: LayoutProps<'/trips/[tripId]'>) {
  const { tripId } = await params
  return <TripShell tripId={tripId}>{children}</TripShell>
}
