import { useState } from 'react'
import { FileCheck, FileSearch, CheckCircle2, XCircle, FileText, User } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { verifyCertificate, type Certificate } from '@/data/mockdata'

export default function CertificatesPage() {
  const { t } = useI18n()
  const { isAuthenticated, role } = useAuth()

  const [cadastralId, setCadastralId] = useState('')
  const [ownerName, setOwnerName] = useState('')
  const [issuedCertificate, setIssuedCertificate] = useState<string | null>(null)

  const [certificateId, setCertificateId] = useState('')
  const [verifyResult, setVerifyResult] = useState<Certificate | null | undefined>(undefined)
  const [isVerifying, setIsVerifying] = useState(false)

  const handleIssueCertificate = async () => {
    if (!cadastralId || !ownerName) return

    await new Promise((resolve) => setTimeout(resolve, 1000))

    const newCertId = `CERT-${Date.now().toString(36).toUpperCase()}`
    setIssuedCertificate(newCertId)
    setCadastralId('')
    setOwnerName('')
  }

  const handleVerifyCertificate = async () => {
    if (!certificateId) return

    setIsVerifying(true)
    setVerifyResult(undefined)

    await new Promise((resolve) => setTimeout(resolve, 1000))

    const result = verifyCertificate(certificateId)
    setVerifyResult(result)
    setIsVerifying(false)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <FileCheck className="h-8 w-8 text-primary" />
          </div>
          <h1 className="mb-2 text-3xl font-bold text-foreground">{t('certificateCenter')}</h1>
          <p className="text-muted-foreground">
            Request and verify land use compliance certificates
          </p>
        </div>

        <Tabs defaultValue="verify" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="request" className="gap-2">
              <FileText className="h-4 w-4" />
              {t('requestCertificate')}
            </TabsTrigger>
            <TabsTrigger value="verify" className="gap-2">
              <FileSearch className="h-4 w-4" />
              {t('verifyCertificate')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="request">
            <Card>
              <CardHeader>
                <CardTitle>{t('requestCertificate')}</CardTitle>
                <CardDescription>
                  Submit a request for a land use compliance certificate
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!isAuthenticated || role === 'guest' ? (
                  <Alert>
                    <User className="h-4 w-4" />
                    <AlertTitle>Authentication Required</AlertTitle>
                    <AlertDescription>
                      You need to be logged in to request certificates.{' '}
                      <Link to="/login" className="font-medium text-primary underline">
                        Login here
                      </Link>
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="cadastralId">{t('cadastralId')}</Label>
                      <Input
                        id="cadastralId"
                        placeholder="CAD-XXXXXX"
                        value={cadastralId}
                        onChange={(e) => setCadastralId(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="ownerName">{t('ownerName')}</Label>
                      <Input
                        id="ownerName"
                        placeholder="Juan Perez"
                        value={ownerName}
                        onChange={(e) => setOwnerName(e.target.value)}
                      />
                    </div>
                    <Button
                      onClick={handleIssueCertificate}
                      disabled={!cadastralId || !ownerName}
                      className="w-full gap-2"
                    >
                      <FileCheck className="h-4 w-4" />
                      {t('issueCertificate')}
                    </Button>

                    {issuedCertificate && (
                      <Alert className="border-primary/50 bg-primary/10">
                        <CheckCircle2 className="h-4 w-4 text-primary" />
                        <AlertTitle className="text-primary">{t('certificateIssued')}</AlertTitle>
                        <AlertDescription>
                          Your certificate ID is:{' '}
                          <code className="rounded bg-primary/20 px-2 py-1 font-mono text-primary">
                            {issuedCertificate}
                          </code>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="verify">
            <Card>
              <CardHeader>
                <CardTitle>{t('verifyCertificate')}</CardTitle>
                <CardDescription>
                  Enter a certificate ID to verify its authenticity
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="verifyId">{t('certificateId')}</Label>
                  <Input
                    id="verifyId"
                    placeholder="CERT-XXXXXX"
                    value={certificateId}
                    onChange={(e) => setCertificateId(e.target.value)}
                  />
                </div>
                <Button
                  onClick={handleVerifyCertificate}
                  disabled={!certificateId || isVerifying}
                  className="w-full gap-2"
                >
                  <FileSearch className="h-4 w-4" />
                  {isVerifying ? 'Verifying...' : t('verify')}
                </Button>

                {verifyResult !== undefined &&
                  (verifyResult ? (
                    <Alert className="border-primary/50 bg-primary/10">
                      <CheckCircle2 className="h-4 w-4 text-primary" />
                      <AlertTitle className="text-primary">{t('valid')}</AlertTitle>
                      <AlertDescription className="mt-2 space-y-1 text-foreground">
                        <p>
                          <strong>{t('cadastralId')}:</strong> {verifyResult.cadastralId}
                        </p>
                        <p>
                          <strong>{t('ownerName')}:</strong> {verifyResult.ownerName}
                        </p>
                        <p>
                          <strong>{t('date')}:</strong> {verifyResult.issueDate}
                        </p>
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <Alert variant="destructive">
                      <XCircle className="h-4 w-4" />
                      <AlertTitle>{t('invalid')}</AlertTitle>
                      <AlertDescription>{t('certificateInvalid')}</AlertDescription>
                    </Alert>
                  ))}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
